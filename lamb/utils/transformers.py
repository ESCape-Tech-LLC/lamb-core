# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import enum

from typing import Type, TypeVar
from datetime import datetime
from django.conf import settings

from lamb.exc import InvalidParamValueError

__all__ = [
    'transform_boolean', 'transform_date', 'transform_string_enum',
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
    elif isinstance(value, (int, float)):
        if value == 0.0:
            return False
        else:
            return True
    else:
        raise InvalidParamTypeError('Invalid data type for boolean convert')

def transform_date(value, format=settings.LAMB_RESPONSE_DATE_FORMAT):
    if isinstance(value, datetime):
        return value
    elif isinstance(value, str):
        try:
            if value.lower() == 'today':
                result = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999)
            else:
                result = datetime.strptime(value, format)
            return result
        except Exception as e:
            raise InvalidParamValueError(
                'Invalid to convert date from string=%s according to format=%s' % (value, format)) from e
    else:
        raise InvalidParamTypeError('Invalid data type for date convert')


T = TypeVar('T')

def transform_string_enum(value: str, enum_class: Type[T]) -> T:
    if isinstance(value, enum_class):
        return value

    # check data types
    if not issubclass(enum_class, enum.Enum) and not issubclass(enum_class, str):
        logger.warning('transform_string_enum received object of class %s as enum_class arg' % enum_class)
        raise ServerError('Invalid class type for enum converting')
    if not isinstance(value, str):
        logger.warning('transform_string_enum received object of class %s as value arg' % value.__class__.__name__)
        raise ServerError('Invalid class type for enum converting')

    # try to convert
    try:
        for enum_candidate in enum_class:
            if value.lower() == enum_candidate.value.lower():
                return enum_class(enum_candidate)
    except ApiError:
        raise
    except Exception as e:
        raise InvalidParamValueError('Failed to convert enum value %s' % value) from e
