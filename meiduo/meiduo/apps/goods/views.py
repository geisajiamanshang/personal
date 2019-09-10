import datetime
import http
from venv import logger

from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render
from django.utils import timezone
from django.views.generic.base import View

from meiduo.apps.goods import constants
from meiduo.apps.goods.models import GoodsCategory, SKU, GoodsVisitCount
from meiduo.apps.oauth.models import BaseModel
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

class DetailView(View):
    def get(self,request,sku_id):
        '''
        获取商品详情
        :param request:
        :param sku_id:
        :return:
        '''

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return render(request,'404.html')

        categories = get_categories()
        # 分类数据
        categories = get_categories()

        # 获取面包屑导航
        breadcrumb = get_breadcrumb(sku.category)

        # 获取spu
        spu = sku.spu

        # 获取规格信息：sku===>spu==>specs
        specs = spu.specs.order_by('id')

        # 查询所有的sku，如华为P10的所有库存商品
        skus = spu.skus.order_by('id')
        '''
        {
            选项:sku_id
        }
        说明：键的元组中，规格的索引是固定的
        示例数据如下：
        {
            (1,3):1,
            (2,3):2,
            (1,4):3,
            (2,4):4
        }
        '''
        sku_options = {}
        sku_option = []
        for sku1 in skus:
            infos = sku1.specs.order_by('spec_id')
            option_key = []
            for info in infos:
                option_key.append(info.option_id)
                # 获取当前商品的规格信息
                if sku.id == sku1.id:
                    sku_option.append(info.option_id)
            sku_options[tuple(option_key)] = sku1.id

        # 遍历当前spu所有的规格
        specs_list = []
        for index, spec in enumerate(specs):
            option_list = []
            for option in spec.options.all():
                # 如果当前商品为蓝、64,则列表为[2,3]
                sku_option_temp = sku_option[:]
                # 替换对应索引的元素：规格的索引是固定的[1,3]
                sku_option_temp[index] = option.id
                # 为选项添加sku_id属性，用于在html中输出链接
                option.sku_id = sku_options.get(tuple(sku_option_temp), 0)
                # 添加选项对象
                option_list.append(option)
            # 为规格对象添加选项列表
            spec.option_list = option_list
            # 重新构造规格数据
            specs_list.append(spec)

        context = {
            'sku': sku,
            'categories': categories,
            'breadcrumb': breadcrumb,
            'category_id': sku.category_id,
            'spu': spu,
            'specs': specs_list
        }
        return render(request,'detail.html',context)


class DetailVisitView(View):
    def post(self,request,category_id):
        '''
        记录分类商品的访问量

        :param request:
        :return:
        '''
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('缺少必传参数')
        t = timezone.localtime()
        today_str = '%d-%02d-%02d' % (t.year,t.month,t.day)
        # 将字符串转化为日期格式
        today_date = datetime.datetime.striptime(today_str,'%Y-%m-%d')

        try:
            counts_data = category.goodsvisitcount_set.get(date=today_date)
        except GoodsVisitCount.DoesNotExist:
            # 如果改类别的商品今天没有访问记录就新建一个
            counts_data = GoodsVisitCount()
        try:
            counts_data.category = category
            counts_data.count += 1
            counts_data.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('服务器异常')
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})












