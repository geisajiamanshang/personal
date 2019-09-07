import http
import re

from django.contrib.auth import login
from users.models import User
from django.shortcuts import render, redirect

# Create your views here.
from django.views.generic.base import View

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
        # redis_cli = get_redis_connection('sms_code')
        # sms_code_redis = redis_cli.get(mobile)
        # # 2.判断是否过期
        # if sms_code_redis is None:
        #     return http.HttpResponseForbidden('短信验证码已经过期')
        # # 3.删除短信验证码，不可以使用第二次
        # redis_cli.delete(mobile)
        # redis_cli.delete(mobile + '_flag')
        # # 4.判断是否正确
        # if sms_code_redis.decode() != sms_code:
        #     return http.HttpResponseForbidden('短信验证码错误')

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
