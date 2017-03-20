__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

import json
from django.http import HttpResponse
from marble.json.encoder import JsonEncoder


class JsonResponse(HttpResponse):

    def __init__(self, data=None, status=200, callback=None, request=None):

        super(JsonResponse, self).__init__(
            content_type = 'application/json; charset=utf8',
            status=status
        )
        if data is not None:
            encoder = JsonEncoder(callback, request)
            content = json.dumps(data, indent=2, ensure_ascii=False, default=encoder.default, sort_keys=False)
            self.content = content

    @staticmethod
    def encode_object(object):
        encoder = JsonEncoder()
        result = json.dumps(object, indent=2, ensure_ascii=False, default=encoder.default, sort_keys=False)
        return result