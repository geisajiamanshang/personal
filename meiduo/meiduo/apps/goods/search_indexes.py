from haystack import indexes

from meiduo.apps.goods.models import SKU


class SKUIndex(indexes.SearchIndex,indexes.Indexable):
    '''
    借助haystack由elasticsearch查询
    '''
    text = indexes.CharField(document=True,use_template=True)


    def get_model(self):
        return SKU

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_launched=True)

