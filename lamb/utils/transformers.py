# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging

from datetime import datetime

from django.conf import settings
from lamb.exc import InvalidParamValueError

__all__ = [
    'transform_boolean', 'transform_date'
]

logger = logging.getLogger(__name__)

def transform_boolean(value):
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        result = value.lower()
        if result in ['1', 'true']:
            return True
        elif result in ['0', 'false']:
            return False
        else:
            raise InvalidParamValueError('Invalid value for boolean convert')
    else:
        raise InvalidParamTypeError('Invalid data type for boolean convert')

def transform_date(value, format=settings.LAMB_RESPONSE_DATE_FORMAT):
    if isinstance(value, datetime):
        return value
    elif isinstance(value, str):
        try:
            result = datetime.strptime(value, format)
            return result
        except Exception as e:
            raise InvalidParamValueError(
                'Invalid to convert date from string=%s according to format=%s' % (value, format)) from e
    else:
        raise InvalidParamTypeError('Invalid data type for date convert')
