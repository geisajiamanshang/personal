import http
import random
from venv import logger

from django.shortcuts import render

# Create your views here.
from django.views.generic.base import View
from django_redis import get_redis_connection

from meiduo.apps.verifications import constants
from meiduo.libs import captcha
from meiduo.libs.yuntongxun.sms import CCP
from meiduo.utils.response_code import RETCODE


class ImageCodeView(View):
    def get(self,request,uuid):
        '''
        get imagecode

        :param request:
        :param uuid:
        :return:
        '''
        text,image = captcha.generate_captcha()
        redis_conn = get_redis_connection('verify_code')
        redis_conn.setex('img_%s'%uuid,constants.IMAGE_CODE_EXPIRES,text)
        return http.HttpResponse(image, content_type='image/jpg')

class SMSCodeView(View):
    def get(self,request, mobile): # mobile 是路径传参，图片验证码和唯一编号是从request中获取
        '''
        get smscode

        :param request:
        :param mobile:
        :return:
        '''
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')
        if not all([image_code_client,uuid]):
            return http.JsonResponse({'code':RETCODE.NECESSARYPARAMERR,'errmsg':'缺少必须要传的参数'})

        redis_conn = get_redis_connection('verify_code')
        image_code_server = redis_conn.get('img_%s'% uuid)
        if image_code_server is None:
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'图形验证码失效'})

        try:
            redis_conn.delete('img_%s'% uuid) # 删除图形验证码，避免恶意测试验证码
        except Exception as e:
            logger.error(e)

        image_code_server = image_code_server.decode()
        if image_code_server != image_code_client.lower():
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR, 'errmsg':'图形验证码有错误'})

        sms_code = '%06d' % random.randint(0,999999)
        logger.info(sms_code)
        redis_conn.setex('sms_%s'%mobile,constants.SMS_CODE_EXPIRES,sms_code)

        # 调用容联云
        CCP().send_template_sms(mobile,[sms_code,constants.SMS_CODE_REDIS_EXPIRES//60],constants.SEND_SMS_TEMPLATE_ID)
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'发送短信成功'})




