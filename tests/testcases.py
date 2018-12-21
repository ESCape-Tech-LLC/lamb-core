from json import loads
from django.http.response import HttpResponse
from django.test import SimpleTestCase
from django.core.management import call_command


class LambTestCase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        call_command('alchemy_create', 'tests', force=True, log_level='DEBUG')
        super().setUpClass()

    @staticmethod
    def get_json(response: HttpResponse):
        return loads(response.content)
