from django.test.client import Client
from django.test.utils import override_settings
from django.test import SimpleTestCase


@override_settings(ROOT_URLCONF='tests.middleware.urls')
class MiddlewareTest(SimpleTestCase):
    def test_invalid_param(self):
        client = Client()
        result = client.get('/invalid_param/')
        self.assertEquals(result.status_code, 400)

    def test_unknown(self):
        client = Client()
        result = client.get('/unknown/')
        self.assertEquals(result.status_code, 500)
