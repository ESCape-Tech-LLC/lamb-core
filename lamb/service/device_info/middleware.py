# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging

from typing import Optional
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from lamb import exc
from lamb.utils import dpath_value, LambRequest
from lamb.types import LambLocale

# from .model import DeviceInfo
from lamb.types import DeviceInfo

logger = logging.getLogger(__name__)


__all__ = [
    'DeviceInfoMiddleware'
]


def _transform_empty_string_to_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise exc.InvalidParamTypeError('Invalid data type received for string converter')

    return value if len(value) > 0 else None


class DeviceInfoMiddleware(MiddlewareMixin):

    def process_request(self, request: LambRequest):
        """ Middleware parse and append device info and locale to request """
        # device info parsing
        try:
            # extract info
            device_family = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_FAMILY, str,
                                        transform=_transform_empty_string_to_none, default=None)
            device_platform = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_PLATFORM, str,
                                          transform=_transform_empty_string_to_none, default=None)
            device_os_version = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_OS_VERSION, str,
                                            transform=_transform_empty_string_to_none, default=None)
            device_locale = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_LOCALE, str,
                                        transform=_transform_empty_string_to_none, default=None)
            app_version = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_APP_VERSION, str,
                                      transform=_transform_empty_string_to_none, default=None)
            app_build = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_APP_BUILD, int, default=None)

            # normalize values
            if device_platform is not None:
                device_platform = device_platform.lower()
            if device_locale is not None:
                device_locale = LambLocale.parse(device_locale)

            # construct and store device info
            device_info = DeviceInfo(
                device_family=device_family,
                device_platform=device_platform,
                device_os=device_os_version,
                device_locale=device_locale,
                app_version=app_version,
                app_build=app_build
            )
            logger.debug('Extracted device info: %s' % device_info)
        except Exception as e:
            logger.debug('Device info extract failed due: %s' % e)
            device_info = DeviceInfo()
        request.lamb_device_info = device_info

        # attach device locale
        if device_info.device_locale is not None:
            request.lamb_locale = device_info.device_locale
        else:
            request.lamb_locale = LambLocale.parse(settings.LAMB_DEVICE_DEFAULT_LOCALE)
