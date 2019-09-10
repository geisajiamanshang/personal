import base64
import http
import json
import pickle

from django.shortcuts import render
from django.views.generic.base import View
from django_redis import get_redis_connection

from meiduo.apps.goods.models import SKU
from meiduo.utils.response_code import RETCODE


class Carts(View):
    def post(self,request):
        '''
        增加购物车
        :param request:
        :return:
        '''
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected')

        if not all([sku_id,count,selected]):
            return http.HttpResponseForbidden('参数不齐')

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品不存在')

        try:
            count = int(count)
        except Exception as e:
            return http.HttpResponseForbidden('参数count有误')

        if not isinstance(selected,bool):
            return http.HttpResponseForbidden('参数selected有误')

        # 用户登录则添加到redis，否则添加到cookie
        if request.user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            pl.hincrby('carts_%s' % request.user.id,sku_id,count)
            if selected:
                pl.sadd('selected_%s' % request.user.id,sku_id)
            pl.excute()
            return http.JsonResponse({'code':RETCODE.OK,'errmsg':'添加购物车成功'})
        else:
            # 操作cookie上的购物车
            cart_dict = {}
            if sku_id in cart_dict:
                count += cart_dict[sku_id]['count']
            cart_dict[sku_id] = {
                'count':count,
                'selected':selected
            }
            cart_dict = base64.b64encode(pickle.dumps(cart_dict).decode())
            response = http.JsonResponse({'code':RETCODE.OK,'errmsg':'添加购物车成功'})
            response.set_cookie('carts',cart_dict)
            return response


    def get(self,request):
        '''
        查询购物车
        :param request:
        :return:
        '''
        user = request.user
        if user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s'% user.id)
            cart_dict = {}
            for sku_id,count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count':int(count),
                    'selected':sku_id in cart_selected
                }
            else:
                cookie_cart =request.COOKIES.get('carts')
                if cookie_cart:
                    cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
                else:
                    cart_dict = {}
                sku_ids = cart_dict.keys()
                skus = SKU.objects.filter(id_in=sku_ids)
                cart_skus = []
                for sku in skus:
                    cart_skus.append({
                        'id': sku.id,
                        'name': sku.name,
                        'count': cart_dict.get(sku.id).get('count'),
                        'selected': str(cart_dict.get(sku.id).get('selected')), # 将True，转'True'，方便json解析
                         'default_image_url': sku.default_image_url,
                        'price': str(sku.price),  # 从Decimal('10.2')中取出'10.2'，方便json解析
                        'amount': str(sku.price * cart_dict.get(sku.id).get('count')),

                    })
                    context = {
                        'cart_skus':cart_skus,
                    }
                    return render(request,'cart.html',context)

    def put(self,request):
        '''
        更新购物车数据
        :param request:
        :return:
        '''
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected')

        if not all([sku_id,count,selected]):
            return http.HttpResponseForbidden('参数不齐全')
        try:
            sku = SKU.objects.get('sku_id')
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku不存在')

        try:
            count = int(count)
        except Exception as e:
            return http.HttpResponseForbidden('参数count有误')
        if not isinstance(selected,bool):
            return http.HttpResponseForbidden('参数selected有误')

        user = request.user
        if user.is_authenticated:
            # 修改redis购物车中数据
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            pl.hset('carts_%s' % user.id,sku_id,count)

            if selected:
                pl.sadd('selected_%s' % user.id,sku_id)
            else:
                pl.srem('selected_%s' % user.id,sku_id)
            pl.excute()

            cart_sku = {
                'id':sku_id,
                'count':count,
                'selected':selected,
                'name':sku.name,
                'default_image_url': sku.default_image_url,
                'price': sku.price,
                'amount': sku.price * count,

            }
            return http.JsonResponse({'code':RETCODE.OK,'errmsg':'修改购物车成功','cart_sku':cart_sku})
        else:
            cart_str = request.COOKIEs.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}
            cart_dict[sku_id] = {
                'count':count,
                'selected':selected
            }
        cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).encode()

        cart_sku = {
            'id': sku_id,
            'count': count,
            'selected': selected,
            'name': sku.name,
            'default_image_url': sku.default_image_url,
            'price': sku.price,
            'amount': sku.price * count,

        }
        response = http.JsonResponse({'code':RETCODE.OK,
                                        'errmsg':'修改购物车成功',
                                        'cart_sku':cart_sku})
        response.set_cookie('carts',cookie_cart_str)
        return response

    def delete(self,request):
        '''
        删除购物车
        :param request:
        :return:
        '''
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品不存在')

        user = request.user
        if user and user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            pl.hdel()
            pl.srem()
            pl.execute()
            return  http.JsonResponse({'code': RETCODE.OK,
                                         'errmsg': '删除购物车成功'})
        else:
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_str = {}
            response = http.JsonResponse({'code':RETCODE.OK,'errmsg':'删除购物车成功'})
            if sku_id in cart_dict:
                del cart_dict[sku_id]
                cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
                response.set_cookie('carts',cookie_cart_str)
            return response


class CartsSelectAllView(View):
    def put(self,request):
        json_dict = json.loads(request.body.decode())
        selected = json_dict.get('selected', True)
        if not isinstance(selected,bool):
            return http.HttpResponseForbidden('参数selected有误')

        user = request.user
        if user is not None and user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            cart = redis_conn.hgetall('carts_%s' % user.id)
            sku_id_list = cart.keys()
            if selected:
                redis_conn.sadd('selected_%s' % user.id, *sku_id_list)
            else:
                redis_conn.srem('selected_%s' % user.id, *sku_id_list)
            return http.JsonResponse({'code': RETCODE.OK,'errmsg': '全选购物车成功'})
        else:
            cart = request.COOKIES.get('carts')
            response = http.JsonResponse({'code': RETCODE.OK,  'errmsg': '全选购物车成功'})
            if cart:
                cart = pickle.loads(base64.b64decode(cart.encode()))
                for sku_id in cart:
                    cart[sku_id]['selected'] = selected
                cookie_cart = base64.b64encode(pickle.dumps(cart)).decode()
                response.set_cookie('carts',cookie_cart)
            return response


class CartsSimpleView(View):
    def get(self,request):
        '''
        商品页面右上角是否登录

        :param request:
        :return:
        '''
        user = request.user
        if user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            redis_cart = redis_conn.hgetall('cart_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)

            cart_dict = {}
            for sku_id,count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count':int(count),
                    'selected':sku_id in cart_selected
                }
        else:
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

        cart_skus = []
        sku_ids = cart_dict.keys()
        skus = SKU.objects.filter(id_in=sku_ids)
        for sku in skus:
            cart_skus.append({
                'id': sku.id,
                 'name': sku.name,
                'count': cart_dict.get(sku.id).get('count'),
                'default_image_url': sku.default_image_url

            })
        return http.JsonResponse({'code':RETCODE.OK,  'errmsg':'OK', 'cart_skus':cart_skus})





