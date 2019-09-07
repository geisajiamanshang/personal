from django.conf.urls import url
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    url('^register/$', views.RegisterView.as_view()),


]