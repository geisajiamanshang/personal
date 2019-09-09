import http

from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render
from django.views.generic.base import View

from meiduo.apps.goods import constants
from meiduo.apps.goods.models import GoodsCategory, SKU
from meiduo.utils.breadcrumb import get_breadcrumb
from meiduo.utils.categories import get_categories
from meiduo.utils.response_code import RETCODE


class ListView(View):
    def get(self,request,category_id,page_num):
        '''
        获取商品列表页

        :param request:
        :param category_id:
        :param page_num:
        :return:
        '''
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseNotFound('GoodsCategory不存在')
        categories = get_categories()
        breadcrumb =get_breadcrumb(category)


        # 排序功能
        sort = request.GET.get('sort','default')
        if 'sort' == 'price':
            sortkind = 'price'
        elif 'sort' == 'hot':
            sortkind = '-sales'
        else:
            sort = 'default'
            sortkind = 'create_time'
        skus = SKU.object.filter(category=category,is_launches=True).order_by(sortkind)

        # 创建分页器
        paginator =Paginator(skus,constants.GOODS_LIST_LIMIT)
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            return http.HttpResponseNotFound('empty page')
        total_page = paginator.num_pages

        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'sort':sort,
            'category': category,  # 第三级分类
            'page_skus': page_skus,  # 分页后数据
            'total_page': total_page,  # 总页数
            'page_num': page_num,

        }
        return render(request,'list.html',context)


class HotGoodsView(View):
    def get(self,request,category_id):
        '''
        获取某个分类的热销商品

        :param request:
        :param category_id:
        :return:
        '''
        skus = SKU.objects.filter(category_id=category_id,is_launched=True).order_by('-sales')[:2]
        hot_skus = []
        for sku in skus:
            hot_skus.append({
                'id':sku.id,
                'default_image_url':sku.default_image_url,
                'name':sku.name,
                'price':sku.price
            })

        return http.HttpResponse({'code':RETCODE.OK,'errmsg':'OK','hot_skus':hot_skus})












