import logging

import babel
from sqlalchemy import types
from sqlalchemy_utils.types.scalar_coercible import ScalarCoercible

from lamb.exc import InvalidParamValueError, ServerError
from lamb.lamb_settings import settings
from lamb.json.mixins import ResponseEncodableMixin

__all__ = ["LambLocale", "LambLocaleType"]

logger = logging.getLogger(__name__)


# info class
class LambLocale(ResponseEncodableMixin, babel.Locale):
    @classmethod
    def parse(cls, identifier, sep="_", resolve_likely_subtags=True):
        exceptions = list()
        seps = {sep, *settings.LAMB_DEVICE_INFO_LOCALE_VALID_SEPS}
        for sep in seps:
            try:
                return super().parse(identifier=identifier, sep=sep, resolve_likely_subtags=resolve_likely_subtags)
            except Exception as e:
                exceptions.append(e)
        if exceptions:
            logger.debug(f"Can not parse Device Locale with seps: {seps} cause {exceptions[0]}")
            raise exceptions[0]

    def response_encode(self, request=None):
        return str(self)


# database storage suport
class LambLocaleType(types.TypeDecorator, ScalarCoercible):
    """LambLocaleType based on sqlalchemy_utils LocaleType data field"""

    impl = types.Unicode(10)
    python_type = LambLocale

    def process_bind_param(self, value, dialect):
        if value is None or isinstance(value, str):
            return value

        try:
            return str(value)
        except Exception as e:
            raise ServerError("Invalid object type received for store as locale") from e

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        try:
            return LambLocale.parse(value)
        except (ValueError, babel.UnknownLocaleError) as e:
            raise ServerError("Locale fields configured invalid") from e

    def _coerce(self, value):
        if value is None or isinstance(value, LambLocale):
            return value

        try:
            return LambLocale.parse(value)
        except (ValueError, babel.UnknownLocaleError) as e:
            raise InvalidParamValueError(f"Unknown or unsupported locale value {value}") from e

    def process_literal_param(self, value, dialect):
        return str(value)
