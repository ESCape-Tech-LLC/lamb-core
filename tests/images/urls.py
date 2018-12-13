from django.conf.urls import url
from .views import SimpleImageListView

urlpatterns = [
    url(r'^simple_images/?$', SimpleImageListView, name='simple_images_list'),
]
