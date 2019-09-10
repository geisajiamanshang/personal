import base64
import pickle

from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request,user,response):
    '''
    登录后合并cookie数据到redis
    :param request:
    :param user:
    :param response:
    :return:
    '''
    cookie_cart_str = request.COOKIES.get('carts')
    if not cookie_cart_str:
        return response

    cookie_cart_dict = pickle.loads(base64.b64decode(cookie_cart_str.encode()))

    new_cookie_dict = {}
    new_cart_selected_add = []
    new_cart_selected_remove = []
    for sku_id,cookie_dict in cookie_cart_dict.items():
        new_cookie_dict[sku_id] = cookie_dict['count']
        if cookie_dict['selected']:
            new_cart_selected_add.append(sku_id)
        else:
            new_cart_selected_remove.append(sku_id)


    # 将分解好的cookie中的数据new_cart_dict 写入到redis数据库中
    redis_conn = get_redis_connection()
    pl = redis_conn.pipline()
    pl.hmset('carts_%s' % user.id,new_cart_dict)
    if new_cart_selected_add:
        pl.sadd('selected_%s' % user.id, *new_cart_selected_add)
    if new_cart_selected_remove:
        pl.srem('selected_%s' % user.id, *new_cart_selected_remove)
    pl.execute()
    response.delete_cookie('carts')
    return response


