from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r"^invalid_param/?$", views.InvalidParam, name="invalid_param"),
    re_path(r"^unknown/?$", views.unknown, name="unknown"),
]

app_name = "tests"
