import http
import json
import re

from django.contrib.auth import login, authenticate, logout
from django.urls import reverse
from django_redis import get_redis_connection
from users.models import User
from django.shortcuts import render, redirect

# Create your views here.
from django.views.generic.base import View

from meiduo.apps.goods.models import SKU
from meiduo.utils.response_code import RETCODE
from . import constants


class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 接收
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        password2 = request.POST.get('cpwd')
        mobile = request.POST.get('phone')
        sms_code = request.POST.get('msg_code')
        allow = request.POST.get('allow')

        # 验证
        # 1.非空
        if not all([username, password, password2, mobile, sms_code, allow]):
            return http.HttpResponseForbidden('填写数据不完整')
        # 2.用户名
        if not re.match('^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('用户名为5-20个字符')
        if User.objects.filter(username=username).count() > 0:
            return http.HttpResponseForbidden('用户名已经存在')
        # 密码
        if not re.match('^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码为8-20个字符')
        # 确认密码
        if password != password2:
            return http.HttpResponseForbidden('两个密码不一致')
        # 手机号
        if not re.match('^1[3456789]\d{9}$', mobile):
            return http.HttpResponseForbidden('手机号错误')
        if User.objects.filter(mobile=mobile).count() > 0:
            return http.HttpResponseForbidden('手机号存在')
        # 短信验证码
        # 1.读取redis中的短信验证码
        redis_cli = get_redis_connection('sms_code')
        sms_code_redis = redis_cli.get(mobile)
        # 2.判断是否过期
        if sms_code_redis is None:
            return http.HttpResponseForbidden('短信验证码已经过期')
        # 3.删除短信验证码，不可以使用第二次
        redis_cli.delete(mobile)
        redis_cli.delete(mobile + '_flag')
        # 4.判断是否正确
        if sms_code_redis.decode() != sms_code:
            return http.HttpResponseForbidden('短信验证码错误')

        # 处理
        # 1.创建用户对象
        user = User.objects.create_user(
            username=username,
            password=password,
            mobile=mobile
        )
        # 2.状态保持
        login(request, user)


        # 向cookie中写用户名，用于客户端显示
        response = redirect('/')
        response.set_cookie('username', username, max_age=constants.USERNAME_COOKIE_EXPIRES)

        # 响应
        return response

class UsernameCountView(View):
    def get(self,request,username):
        '''
        get the count of the username

        :param request:
        :param username:
        :return:
        '''
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK','count':count})


class MobileCountVIew(View):
    def get(self,request,mobile):
        '''
        judge the number is repeatable

        :param request:
        :param mobile:
        :return:
        '''
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonRsponse({'code':RETCODE.OK,'errmsg':'OK','count':count})

class LoginView(View):
    def get(self,request):
        '''
        获取登录页面

        :param request:
        :return:
        '''
        return render(request,'login.html')

    def post(self, request):
        '''
        login in
        :param request:
        :return:
        '''
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        if not all([username, password]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^[a-zA-Z0-9-_]{5,20}$',username):
            return http.HttpResponseForbidden('输入正确的用户名或手机号')
        if not re.match(r'^[0-9a-zA-Z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')

        user = authenticate(username=username,password=password)
        if user is None:
            return render(request,'login.html', {'account_errmsg':'用户名或者密码错误'})

        login(request,user)
        if remembered != 'on':
            request.session.set_expirty(0)
        else:
            request.session.set_expirty(None) # 默认session记住登录状态是2周
        return redirect(reverse('contents:index'))


class Logout(View):
    def get(self,request):
        '''
        logout
        :param request:
        :return:
        '''
        logout(request)

        response = redirect(reverse('contents:index'))
        response.delete_cookie('username')
        return response

class UserInfoView(View):
    def get(self, request):
        if request.user.is_authenticated():
            return render(request,'user_center_info.html')
        else:
            return redirect(reverse('users:login'))


class UserBrowserHistory(LoginRequiredJSONMixin, View):
    def post(self,request):
        '''
        保存用户浏览记录

        :param request:
        :return:
        '''
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        try:
            sku = SKU.objects.get('sku_id')
        except:
            return http.HttpResponseForbidden('sku不存在')

        # 浏览记录保存在内存中
        redis_conn = get_redis_connection('history')
        pl = redis_conn.pipeline()
        user_id = request.user.id

        pl.lrem('history_%s' % user_id,0,sku_id)
        pl.lpush('history_%s' % user_id,sku_id)
        pl.ltrim('history_%s' % user_id,0,4)
        pl.execute()

        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})

    def get(self,request):
        '''
        获取用户浏览记录

        :param request:
        :return:
        '''
        redis_conn = get_redis_connection('history')
        sku_ids = redis_conn.lrange('history_%s' % request.user.id,0,4)
        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
        skus.append({
            'id':sku_id,
            'name':sku.name,
            'default_image_url':sku.default_image_url,
            'price':sku.price

        })
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})
