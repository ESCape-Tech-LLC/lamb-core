# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import babel

from sqlalchemy import types

from lamb.exc import ServerError, InvalidParamValueError, InvalidParamTypeError
from lamb.json.mixins import ResponseEncodableMixin

# TODO: fix
from sqlalchemy_utils.types.scalar_coercible import ScalarCoercible
from lamb.types.scalar_coercible import ScalarCoercible

__all__ = [
    'LambLocale', 'LambLocaleType'
]

logger = logging.getLogger(__name__)


# info class
class LambLocale(ResponseEncodableMixin, babel.Locale):
    def response_encode(self, request=None):
        return str(self)


# database storage suport
class LambLocaleType(types.TypeDecorator, ScalarCoercible):
    """ LambLocaleType based on LocaleType data field """

    impl = types.Unicode(10)
    python_type = LambLocale

    def process_bind_param(self, value, dialect):
        if value is None or isinstance(value, str):
            return value

        try:
            return str(value)
        except Exception as e:
            raise ServerError(f'Invalid object type received for store as locale') from e

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        try:
            return LambLocale.parse(value)
        except (ValueError, babel.UnknownLocaleError) as e:
            raise ServerError('Locale fields configured invalid') from e

    def _coerce(self, value):
        if value is None or isinstance(value, LambLocale):
            return value

        try:
            return LambLocale.parse(value)
        except (ValueError, babel.UnknownLocaleError) as e:
            raise InvalidParamValueError('Unknown or unsupported locale value %s' % value)

    def process_literal_param(self, value, dialect):
        return str(value)
