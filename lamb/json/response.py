# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import json
import xmltodict

from django.http import HttpResponse
from django.conf import settings

from lamb.json.encoder import JsonEncoder


__all__ = ['JsonResponse']


class JsonResponse(HttpResponse):

    def __init__(self, data=None, status=200, callback=None, request=None):
        # determine content_type
        if request is not None and \
                'HTTP_ACCEPT' in request.META.keys() \
                and request.META['HTTP_ACCEPT'].lower().startswith('application/xml'):
            content_type = 'application/xml; charset=utf8'
        else:
            content_type = 'application/json; charset=utf8'

        super().__init__(content_type=content_type, status=status)

        if data is not None:
            # encode response in form of json
            encoder = JsonEncoder(callback, request)

            _response_indent = settings.LAMB_RESPONSE_JSON_INDENT

            if _response_indent is not None:
                content = json.dumps(data, indent=_response_indent, ensure_ascii=False, default=encoder.default, sort_keys=False)
            else:
                content = json.dumps(data, ensure_ascii=False, default=encoder.default, sort_keys=False)

            # reparese in form of XML
            if request is not None \
                    and 'HTTP_ACCEPT' in request.META.keys() \
                    and request.META['HTTP_ACCEPT'].lower().startswith('application/xml'):
                content = json.loads(content)
                content = {'response':content}
                content = xmltodict.unparse(content)

            # return result
            self.content = content

    @staticmethod
    def encode_object(object):
        encoder = JsonEncoder()
        result = json.dumps(object, indent=2, ensure_ascii=False, default=encoder.default, sort_keys=False)
        return result
