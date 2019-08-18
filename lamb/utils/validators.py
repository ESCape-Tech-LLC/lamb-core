# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import  logging

from typing import Optional, TypeVar, Sized
from django.core.validators import EmailValidator, ValidationError
from sqlalchemy_utils import PhoneNumber

from lamb.exc import InvalidParamValueError, InvalidParamTypeError, ServerError, ApiError


logger = logging.getLogger(__name__)


__all__ = [
    'validate_range', 'validate_length', 'validate_phone_number', 'validate_email'
]

VT = TypeVar('VT')


def validate_range(value: Optional[VT],
                   min_value: VT,
                   max_value: VT,
                   key: str = None,
                   allow_none: bool = False) -> Optional[VT]:
    """ Value within interval validator

    :param value: Value to be checked
    :param min_value: Interval bottom limit
    :param max_value: Interval top limit
    :param key: Optional key to include in exception description as details
    :param allow_none: Flag to make None value valid returning None

    :raises InvalidParamValueError: In case of value out of interval
    :raises InvalidParamTypeError: In case of any other exception
    """
    if value is None and allow_none:
        return value

    try:
        if value < min_value or value > max_value:
            raise InvalidParamValueError(
                f'Invalid param {key} value or type, should be between {min_value} and {max_value}', error_details=key)
        return value
    except InvalidParamValueError:
        raise
    except Exception as e:
        raise InvalidParamTypeError('Invalid param type for %s' % key, error_details=key) from e


def validate_length(
        value: Optional[VT],
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        key: Optional[str] = None,
        allow_none: bool = False,
        trimming: bool = True) -> Optional[VT]:
    """ Validate value of Sized datatype for min/max length

    :param value: value to be checked
    :param min_length: minimal length (None - skip check)
    :param max_length: maximum length (None - skip check)
    :param key: optional key to include in exception description as details
    :param allow_none: flag to make None value valid returning None
    :param trimming: flag to trim string values (removes whitespace symbols)
    :return: validated value

    :raises InvalidParamValueError: In case of value out of min/max interval
    :raises ServerError: In case of any other exception
    """
    # early return
    if value is None and allow_none:
        return None

    # pre-patch
    if isinstance(value, str) and trimming:
        value = ' '.join(value.split())

    # check data type
    try:
        length = len(value)
    except Exception as e:
        raise InvalidParamTypeError(f'Invalid param type for {key}, that not support length info',
                                    error_details=key) from e

    # check length
    if min_length and max_length and min_length > max_length:
        logger.warning(f'validate_length invalid call: [value = {value}, min={min_length}, max={max_length}]')
        raise ServerError(f'Invalid length check call')
    if min_length is not None and length < min_length:
        raise InvalidParamValueError(f'Field {key} have invalid length. Minimum = {min_length}', error_details=key)
    if max_length is not None and length > max_length:
        raise InvalidParamValueError(f'Field {key} have invalid length. Maximum = {max_length}', error_details=key)

    return value


def validate_phone_number(phone_number: Optional[str], region: Optional[str] = None,
                          allow_none: bool = False) -> PhoneNumber:
    """ Validate value as valid phone number """
    # early return
    if phone_number is None and allow_none:
        return None

    if isinstance(phone_number, PhoneNumber):
        return phone_number

    # parse
    try:
        if region is not None:
            region = region.upper()
        phone_number = PhoneNumber(phone_number, region)
        if not phone_number.is_valid_number():
            raise InvalidParamValueError('Phone number is not valid')
        logger.debug(f'parsed phone number: {phone_number.e164}')
        return phone_number
    except ApiError:
        raise
    except Exception as e:
        raise InvalidParamValueError(f'Phone number validation failed') from e


def validate_email(value: Optional[str], allow_none: bool = False) -> Optional[str]:
    # early return
    if value is None and allow_none:
        return value

    # parse value
    try:
        EmailValidator()(value)
        return value
    except ValidationError as e:
        raise InvalidParamValueError(f'Invalid email format') from e