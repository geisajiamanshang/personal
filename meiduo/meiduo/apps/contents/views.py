from django.shortcuts import render

# Create your views here.
from django.views.generic.base import View

from meiduo.apps.contents.models import ContentCategory
from meiduo.utils.categories import get_categories


class IndexView(View):
    def get(self,request):
        '''
        获取首页广告界面
        :param request:
        :return:
        '''
        # 查询商品频道和分类
        categories = get_categories()
        dict = {}
        content_categories = ContentCategory.objects.all()
        for cat in content_categories:
            dict[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

        context = {
            'categories':categories,
            'content':dict
        }

        return render(request,'index.html',context=context)
