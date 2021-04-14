# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import dataclasses
import json

from typing import Optional
from sqlalchemy import types
from sqlalchemy.dialects.postgresql import JSONB
from lamb import exc
from lamb.types import LambLocale
from lamb.json.mixins import ResponseEncodableMixin


__all__ = [
    'DeviceInfo', 'DeviceInfoType'
]

logger = logging.getLogger(__name__)


@dataclasses.dataclass()
class DeviceInfo(ResponseEncodableMixin, object):
    """A device info class """
    device_family: Optional[str] = None
    device_platform: Optional[str] = None
    device_os: Optional[str] = None
    app_version: Optional[str] = None
    app_build: Optional[int] = None
    device_locale: Optional[LambLocale] = None

    def __post_init__(self):
        if isinstance(self.device_locale, str):
            self.device_locale = LambLocale.parse(self.device_locale)

    def response_encode(self, request=None) -> dict:
        result = dataclasses.asdict(self)
        if self.device_locale is not None:
            result['device_locale'] = self.device_locale.response_encode(request)
        else:
            result['device_locale'] = None
        return result


class DeviceInfoType(types.TypeDecorator):
    """ Database storage """
    impl = types.Unicode(10)
    python_type = DeviceInfo

    def __init__(self, *args, encoder_class=None, **kwargs):
        self._encoder_class = encoder_class
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        # check params
        if value is None:
            return value

        if not isinstance(value, DeviceInfo):
            logger.warning(f'Invalid data type to store as device info: {value}')
            raise exc.ServerError('Invalid data type to store as device info')

        # store data
        result = value.response_encode()
        if dialect.name != 'postgresql':
            result = json.dumps(result, cls=self._encoder_class)
        return result

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        if dialect.name != 'postgresql':
            result = json.loads(value)
        else:
            result = value
        result = DeviceInfo(**result)
        return result

    def process_literal_param(self, value, dialect):
        return str(value)
