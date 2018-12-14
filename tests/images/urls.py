from django.conf.urls import url, include

urlpatterns = [
    url(r'^', include('tests.images.test_urls', namespace='images')),
]
