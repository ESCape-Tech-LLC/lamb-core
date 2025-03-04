from django.urls import re_path

from .views import SimpleImageListView

urlpatterns = [
    re_path(r"^simple_images/?$", SimpleImageListView, name="simple_images_list"),
]

app_name = "tests"
