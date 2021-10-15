# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import dataclasses
import json

from typing import Optional, Dict, Any, TypeVar, Type, List
from sqlalchemy import types
from sqlalchemy.dialects.postgresql import JSONB
from functools import partial
from django.conf import settings
from ipware import get_client_ip

from lamb import exc
from lamb.json.encoder import JsonEncoder
from lamb.types import LambLocale
from lamb.utils import LambRequest, dpath_value, import_by_name
from lamb.utils.validators import validate_length
from lamb.json.mixins import ResponseEncodableMixin
from lamb.ext.geoip import *


__all__ = [
    'DeviceInfo', 'DeviceInfoType', 'device_info_factory', 'get_device_info_class'
]

logger = logging.getLogger(__name__)


# info class
@dataclasses.dataclass()
class DeviceInfo(ResponseEncodableMixin, object):
    """ A device info class """
    device_family: Optional[str] = None
    device_platform: Optional[str] = None
    device_os: Optional[str] = None
    app_version: Optional[str] = None
    app_build: Optional[int] = None
    device_locale: Optional[LambLocale] = None
    ip_address: Optional[str] = None
    ip_routable: Optional[bool] = None
    geoip2_info: Optional[Dict[str, Any]] = None

    # construct
    def __post_init__(self):
        if isinstance(self.device_locale, str):
            self.device_locale = LambLocale.parse(self.device_locale)

    @classmethod
    def parse_request(cls, request: LambRequest) -> Dict[str, Any]:
        try:
            # extract fields
            _transform = partial(validate_length, allow_none=True, empty_as_none=True, trimming=True)

            device_family = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_FAMILY, str,
                                        transform=_transform, default=None)
            device_platform = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_PLATFORM, str,
                                          transform=_transform, default=None)
            device_os_version = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_OS_VERSION, str,
                                            transform=_transform, default=None)
            device_locale = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_LOCALE, str,
                                        transform=_transform, default=None)
            app_version = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_APP_VERSION, str,
                                      transform=_transform, default=None)
            app_build = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_APP_BUILD, int, default=None)

            # ip/geo fields
            if settings.LAMB_DEVICE_INFO_COLLECT_IP:
                ip_address, ip_routable = get_client_ip(request)
            else:
                ip_address, ip_routable, geoip2_info = None, None, None

            if ip_address is not None and settings.LAMB_DEVICE_INFO_COLLECT_GEO:
                geoip2_info = {}

                try:
                    country_info = get_country_info(ip_address)
                    geoip2_info['country'] = {
                        'gid': country_info.country.geoname_id,
                        'name': country_info.country.name
                    } if country_info is not None else None
                except Exception as e:
                    logger.debug(f'device_info geoip2 country parsing failed: {e}')
                    geoip2_info['country'] = None
                    pass

                try:
                    city_info = get_city_info(ip_address)
                    geoip2_info['city'] = {
                        'gid': city_info.city.geoname_id,
                        'name': city_info.city.name,
                        'confidence': city_info.city.confidence
                    } if city_info is not None else None
                except Exception as e:
                    logger.debug(f'device_info geoip2 city parsing failed: {e}')
                    geoip2_info['city'] = None
                    pass

                try:
                    asn_info = get_asn_info(ip_address)
                    geoip2_info['asn'] = {
                        'number': asn_info.autonomous_system_number,
                        'org': asn_info.autonomous_system_organization
                    } if asn_info is not None else None
                except Exception as e:
                    logger.debug(f'device_info geoip2 asn parsing failed: {e}')
                    geoip2_info['asn'] = None
                    pass
            else:
                geoip2_info = None

            # normalize values
            if device_platform is not None:
                device_platform = device_platform.lower()
            if device_locale is not None:
                device_locale = LambLocale.parse(device_locale)

            # construct and store device info
            result = dict(
                device_family=device_family,
                device_platform=device_platform,
                device_os=device_os_version,
                device_locale=device_locale,
                app_version=app_version,
                app_build=app_build,
                ip_address=ip_address,
                ip_routable=ip_routable,
                geoip2_info=geoip2_info
            )
        except Exception as e:
            logger.warning(f'DeviceInfo request parsing failed due: {e}')
            result = {}

        return result

    # serialize
    def to_json(self, request=None) -> dict:
        """ Base encoding method - serialize all data """
        result = dataclasses.asdict(self)
        if self.device_locale is not None:
            result['device_locale'] = self.device_locale.response_encode(request)
        else:
            result['device_locale'] = None

        return result

    def response_encode(self, request=None) -> dict:
        """ REST support serialize - include fields hiding """
        result = self.to_json(request)
        result.pop('ip_address', None)
        result.pop('ip_routable', None)
        result.pop('geoip2_info', None)
        return result


# dynamic factory
DT = TypeVar('DT', bound=DeviceInfo)


_cached_device_info_class = None


def get_device_info_class() -> Type[DT]:
    global _cached_device_info_class

    if _cached_device_info_class is None:
        _cached_device_info_class = import_by_name(settings.LAMB_DEVICE_INFO_CLASS)
        logger.info(f'device info class would be used: {_cached_device_info_class}')

    return _cached_device_info_class


def device_info_factory(request: LambRequest) -> DeviceInfo:
    di_class = get_device_info_class()
    result = di_class(**di_class.parse_request(request))
    return result


# database storage support
class DeviceInfoType(types.TypeDecorator):
    """ Database storage """
    impl = types.VARCHAR
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
        result = value.to_json()
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
        result = get_device_info_class()(**result)
        return result

    def process_literal_param(self, value, dialect):
        return str(value)
