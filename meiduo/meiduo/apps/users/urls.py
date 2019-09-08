from django.conf.urls import url
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    url(r'^register/$', views.RegisterView.as_view()),
    url(r'^/usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$', views.UsernameCountView.as_view()),
    url(r'^/mobiles/(?P<mobile>1[3-9]\d{9})/count/$',views.MobileCountVIew.as_view()),

]