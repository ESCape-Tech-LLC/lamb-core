import json
import uuid
import logging
import datetime
from decimal import Decimal

from django.conf import settings

# SQLAlchemy
from sqlalchemy_utils import PhoneNumber

# Lamb Framework
from lamb.utils import import_by_name
from lamb.json.mixins import ResponseEncodableMixin

__all__ = ["JsonEncoder"]

logger = logging.getLogger(__name__)


class JsonEncoder(json.JSONEncoder):
    def __init__(self, callback=None, request=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.request = request
        self._datetime_transformer = import_by_name(settings.LAMB_RESPONSE_DATETIME_TRANSFORMER)

    def default(self, obj):
        # general encoding
        if isinstance(obj, datetime.datetime):
            result = self._datetime_transformer(obj)
        elif isinstance(obj, datetime.date):
            result = obj.strftime(settings.LAMB_RESPONSE_DATE_FORMAT)
        elif isinstance(obj, Decimal):
            result = float(obj)
        elif isinstance(obj, uuid.UUID):
            result = str(obj)
        elif isinstance(obj, set):
            result = list(obj)
        elif isinstance(obj, PhoneNumber):
            result = obj.e164
        elif isinstance(obj, ResponseEncodableMixin):
            result = obj.response_encode(self.request)
        else:
            result = json.JSONEncoder.default(self, obj)

        # Advanced encoding for callback
        if self.callback is not None:
            result = self.callback(obj, result, self.request)

        return result
