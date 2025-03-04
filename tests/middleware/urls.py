from django.urls import include, re_path

urlpatterns = [
    re_path(r"^", include("tests.middleware.test_urls", namespace="tests")),
]

handler404 = "lamb.utils.default_views.page_not_found"

handler400 = "lamb.utils.default_views.bad_request"

handler500 = "lamb.utils.default_views.server_error"
