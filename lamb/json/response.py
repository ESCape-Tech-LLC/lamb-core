# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import json
import xmltodict

from django.http import HttpResponse
from django.conf import settings

from lamb.json.encoder import JsonEncoder
from lamb.utils import import_by_name

try:
    import orjson
except ImportError:
    orjson = None


__all__ = ['JsonResponse']

_encoder_class = None


class JsonResponse(HttpResponse):

    def __init__(self, data=None, status=200, callback=None, request=None):
        # determine content_type
        content_type = 'application/json; charset=utf8'

        super().__init__(content_type=content_type, status=status)

        if data is not None:
            # encode response in form of json
            global _encoder_class
            if _encoder_class is None:
                _encoder_class = import_by_name(settings.LAMB_RESPONSE_ENCODER)
            encoder = _encoder_class(callback, request)

            _response_indent = settings.LAMB_RESPONSE_JSON_INDENT

            if orjson is not None:
                if _response_indent is not None:
                    options = orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE | orjson.orjson.OPT_PASSTHROUGH_DATETIME
                else:
                    options = 0 | orjson.OPT_PASSTHROUGH_DATETIME
                content = orjson.dumps(data, default=encoder.default, option=options)
            else:
                if _response_indent is not None:
                    content = json.dumps(data, indent=_response_indent, ensure_ascii=False, default=encoder.default, sort_keys=False)
                else:
                    content = json.dumps(data, ensure_ascii=False, default=encoder.default, sort_keys=False)

            # return result
            self.content = content

    @staticmethod
    def encode_object(object):
        encoder = JsonEncoder()
        result = json.dumps(object, indent=2, ensure_ascii=False, default=encoder.default, sort_keys=False)
        return result
