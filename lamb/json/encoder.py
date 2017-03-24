__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

import json
import datetime
import time
import uuid
from decimal import Decimal
from collections import OrderedDict

from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import inspect

class JsonMixin(object):
    def json_advance_encode(self, encoded_object):
        """
        :param encoded_object:  Encoded to dictionary representation of self
        :type encoded_object: dict
        :return: Encoded representation with additional values or removed some values
        :rtype: dict
        """
        raise NotImplementedError('JsonMixin json_advance_encode method is abstract '
                                  'and should be overridden in subclass')

class JsonEncoder(json.JSONEncoder):

    def __init__(self, callback=None, request=None):
        super(JsonEncoder, self).__init__()
        self.callback = callback
        self.request = request

    def default(self, obj):
        # general encoding
        if isinstance(obj, datetime.datetime):
            result = int(time.mktime(obj.timetuple()))
        elif isinstance(obj, datetime.date):
            result = obj.strftime('%Y-%m-%d')
        elif isinstance(obj, Decimal):
            result = float(obj)
        elif isinstance(obj, uuid.UUID):
            result = str(obj)
        elif isinstance(obj.__class__, DeclarativeMeta):
            result = dict()
            # result = OrderedDict()
            ins = inspect(obj)
            for column in ins.mapper.column_attrs.keys():
                result[column] = getattr(obj, column)
            #TODO: inspect relationships
        else:
            result = json.JSONEncoder.default(self, obj)

        # Advanced encoding for JsonMixin
        if isinstance(obj, JsonMixin):
            result = obj.json_advance_encode(result)

        # Advanced encoding for callback
        if self.callback is not None:
            result = self.callback(obj, result, self.request)

        return result
