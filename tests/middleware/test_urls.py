from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^invalid_param/?$', views.InvalidParam, name='invalid_param'),
    url(r'^unknown/?$', views.unknown, name='unknown'),
]

app_name = 'tests'
