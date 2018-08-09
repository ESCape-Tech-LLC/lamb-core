# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import babel

from sqlalchemy import types
from sqlalchemy_utils.types.scalar_coercible import ScalarCoercible

from lamb.exc import ServerError, InvalidParamValueError
from lamb.json.mixins import ResponseEncodableMixin

__all__ = [
    'LambLocale', 'LambLocaleType'
]

logger = logging.getLogger(__name__)


class LambLocale(ResponseEncodableMixin, babel.Locale):
    def response_encode(self, request=None):
        return str(self)


class LambLocaleType(types.TypeDecorator, ScalarCoercible):
    """
    LambLocaleType based on sqlalchemy_utils LocaleType data field.
    """

    impl = types.Unicode(10)
    python_type = LambLocale

    def process_bind_param(self, value, dialect):
        if isinstance(value, LambLocale):
            return str(value)

        if isinstance(value, str):
            return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return LambLocale.parse(value)
            except (ValueError, babel.UnknownLocaleError) as e:
                raise ServerError('Locale fields configured invalid') from e

    def _coerce(self, value):
        if value is not None and not isinstance(value, LambLocale):
            try:
                return LambLocale.parse(value)
            except (ValueError, babel.UnknownLocaleError) as e:
                raise InvalidParamValueError('Unknown or unsupported locale value %s' % value)
        return value
