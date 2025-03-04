from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.test.client import Client


@override_settings(ROOT_URLCONF="tests.middleware.urls")
class MiddlewareTest(SimpleTestCase):
    def test_invalid_param(self):
        client = Client()
        result = client.get("/invalid_param/")
        self.assertEqual(result.status_code, 400)

    def test_unknown(self):
        client = Client()
        result = client.get("/unknown/")
        self.assertEqual(result.status_code, 500)
