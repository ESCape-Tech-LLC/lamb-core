__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

import json
import xmltodict
from django.http import HttpResponse
from lamb.json.encoder import JsonEncoder

__all__ = [
    'JsonResponse'
]

class JsonResponse(HttpResponse):

    def __init__(self, data=None, status=200, callback=None, request=None):

        # determine content_type

        if request is not None and \
                'HTTP_ACCEPT' in request.META.keys() \
                and request.META['HTTP_ACCEPT'] == 'application/xml':
            content_type = 'application/xml; charset=utf8'
        else:
            content_type = 'application/json; charset=utf8'

        super(JsonResponse, self).__init__(
            content_type = content_type,
            status=status
        )
        if data is not None:
            encoder = JsonEncoder(callback, request)
            content = json.dumps(data, indent=2, ensure_ascii=False, default=encoder.default, sort_keys=False)

            if request is not None and 'HTTP_ACCEPT' in request.META.keys() and request.META['HTTP_ACCEPT'] == 'application/xml':
                encoded_data = json.loads(content)
                content = json.loads(content)
                content = {'response':content}
                content = xmltodict.unparse(content)
            self.content = content

    @staticmethod
    def encode_object(object):
        encoder = JsonEncoder()
        result = json.dumps(object, indent=2, ensure_ascii=False, default=encoder.default, sort_keys=False)
        return result