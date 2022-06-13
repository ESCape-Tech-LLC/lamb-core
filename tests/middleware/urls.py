from django.conf.urls import url, include

urlpatterns = [
    url(r"^", include("tests.middleware.test_urls", namespace="tests")),
]

handler404 = "lamb.utils.default_views.page_not_found"

handler400 = "lamb.utils.default_views.bad_request"

handler500 = "lamb.utils.default_views.server_error"
