# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import dataclasses
import json

from typing import Optional
from dataclasses import dataclass
from sqlalchemy import types
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_utils.types.scalar_coercible import ScalarCoercible
from lamb import exc
from lamb.json.encoder import JsonEncoder
from lamb.types import LambLocale


__all__ = [
    'DeviceInfo', 'DeviceInfoType'
]

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class DeviceInfo(object):
    """A device info class """
    device_family: Optional[str] = None
    device_platform: Optional[str] = None
    device_os: Optional[str] = None
    app_version: Optional[str] = None
    app_build: Optional[int] = None
    device_locale: Optional[LambLocale] = None


class DeviceInfoType(types.TypeDecorator, ScalarCoercible):
    """ Database storage """
    impl = types.Unicode(10)
    python_type = DeviceInfo

    def __init__(self, *args, encoder_class=JsonEncoder, **kwargs):
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
        if dialect.name == 'postgresql':
            value = dataclasses.asdict(value)
        else:
            value = json.dumps(value, cls=self._encoder_class)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        if dialect.name != 'postgresql':
            value = json.loads(value)

        return DeviceInfo(**value)
