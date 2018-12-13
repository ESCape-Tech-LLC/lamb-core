from json import loads
from django.http.response import HttpResponse
from django.test import SimpleTestCase


class LambTestCase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        from lamb.db.session import metadata
        metadata.drop_all()
        metadata.create_all()
        super().setUpClass()

    @staticmethod
    def get_json(response: HttpResponse):
        return loads(response.content)
