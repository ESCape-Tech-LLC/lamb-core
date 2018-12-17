# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


import json
import datetime
import time
import uuid

from django.conf import settings
from decimal import Decimal

from lamb.json.mixins import ResponseEncodableMixin


__all__ = ['JsonEncoder']


class JsonEncoder(json.JSONEncoder):

    def __init__(self, callback=None, request=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.request = request

    def default(self, obj):
        # general encoding
        if isinstance(obj, datetime.datetime):
            result = int(time.mktime(obj.timetuple()))
        elif isinstance(obj, datetime.date):
            result = obj.strftime(settings.LAMB_RESPONSE_DATE_FORMAT)
        elif isinstance(obj, Decimal):
            result = float(obj)
        elif isinstance(obj, uuid.UUID):
            result = str(obj)
        elif isinstance(obj, ResponseEncodableMixin):
            result = obj.response_encode(self.request)
        else:
            result = json.JSONEncoder.default(self, obj)

        # Advanced encoding for callback
        if self.callback is not None:
            result = self.callback(obj, result, self.request)

        return result
