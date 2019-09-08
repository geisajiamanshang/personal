import re
from venv import logger

from QQLoginTool.QQtool import OAuthQQ
from django import http
from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import render, redirect

# Create your views here.
from django.urls import reverse
from django.views.generic.base import View
from django_redis import get_redis_connection

from meiduo.apps.oauth.models import OAuthQQUser
from meiduo.apps.users.models import User
from meiduo.utils.response_code import RETCODE


class QQURLView(View):
    def get(self,request):
        next = request.GET.get('next')
        oauth = OAuthQQ(
            client_id=settings.QQ_CLIENT_ID,
            client_secret=settings.QQ_CLIENT_SECRET,
            redirect_uri=settings.QQ_REDIRECT_URI,
            state = next
        )
        login_url = oauth.get_qq_url()
        return http.HttpResponse({'code':RETCODE.OK,'errmsg':'OK','login_url':login_url})

class QQUserView(View):
    def get(self,request):
        '''
        拿到qq登录用户信息来登录

        :param request:
        :return:
        '''
        code = request.GET.get('code')
        if not code:
            return http.HttpResponse('缺少code')
        oauth = OAuthQQ(
            client_id=settings.QQ_CLIENT_ID,
            client_secret=settings.QQ_CLIENT_SECRET,
            redirect_uri=settings.QQ_REDIRECT_URI,

        )
        try:
            access_token = oauth.get_access_token(code)
            open_id = oauth.get_open_id(access_token)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('OAuth2.0验证失败')

        try:
            oauth_user = OAuthQQUser.objects.get(openid=open_id)
        except OAuthQQUser.DoesNotExist:
            # 如果没有，open_id变成access_token去客户端拿用户信息，渲染回调地址
            access_token = generate_access_token(open_id)
            context = {'access_token':access_token}
            return render(request,'oauth_callback.html',context=context)
        else:
            # qq登录用户存在，直接登录
            qq_user = oauth_user.user
            login(request,qq_user)
            response = redirect(reverse('contents:index'))
            response.set_cookie('username',qq_user.username,max_age=14*24*3600)
            return response

    def post(self,request):
        '''
        当qq登录用户信息中没有用户信息的时候要去User类中找，没有的话注册
        :param self:
        :param request:
        :return:
        '''
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        sms_code_client = request.POST.get('sms_code')
        access_token = request.POST.get('access_token')

        if not all([mobile,password,sms_code_client,access_token]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')
# 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s'% mobile)
        if sms_code_server is None:
            return render(request,'oauth_callback.html',{'sms_code_errmsg':'无效的短信验证码'})

        sms_code_server = sms_code_server.decode()
        if sms_code_server.lower() != sms_code_client:
                return render(request,'oauth_callback.html',{'sms_code_errmsg':'输入的短信验证码错误'})

        openid = check_access_token(access_token)
        if not openid:
            return render(request,'oauth_callback.html',{'openid_errmsg':'无效的openid'})

        # 查看user中是否有，有的话创建一个oauthqquser，没有的话注册用户信息后绑定
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            user = User.objects.create_user(username=mobile,password=password,mobile=mobile)
        else:
            # 用户存在
            if not user.check_password(password):
                return render(request,'oauth_callback.html',{'account_errmsg':'用户名或密码错误'})
        # 成为qq登录用户
        try:
            OAuthQQUser.objects.create(openid=openid,user=user)
        except OAuthQQUser.DatabaseError as e:
            return render(request,'oauth_callback.html',{'qq_login_errmsg':'qq登录失败'})

        login(request,user)
        next = request.GET.get('next')
        if next:
            response = redirect(next)
        else:
            response = redirect(reverse('contents:index'))
        response.set_cookie('username',user.username,max_age=14*24*3600)
        return response