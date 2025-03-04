from django.urls import re_path, include

urlpatterns = [
    re_path(r"^", include("tests.images.test_urls", namespace="images")),
]

handler404 = "lamb.utils.default_views.page_not_found"

handler400 = "lamb.utils.default_views.bad_request"

handler500 = "lamb.utils.default_views.server_error"
