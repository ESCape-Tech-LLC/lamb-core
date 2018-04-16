# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging

from django.conf import settings
from lamb.utils import dpath_value
from .model import DeviceInfo

logger = logging.getLogger(__name__)


__all__ = [
    'DeviceInfoMiddleware'
]


class DeviceInfoMiddleware(object):

    def process_request(self, request):
        """
        :param request: Request object
        :type request: F2CRequest
        """
        try:
            device_family = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_FAMILY, str, allow_none=True)
            device_platform = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_PLATFORM, str, allow_none=True)
            device_os_version = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_OS_VERSION, str, allow_none=True)
            device_locale = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_LOCALE, str, allow_none=True)
            app_version = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_APP_VERSION, str, allow_none=True)
            app_build = dpath_value(request.META, settings.LAMB_DEVICE_INFO_HEADER_APP_BUILD, int, allow_none=True)

            # normalize
            if device_platform is not None:
                device_platform = device_platform.lower()
            if device_family is not None:
                device_family = device_family.lower()
            if device_locale is not None:
                device_locale = device_locale.lower()

            # combine device info
            device_info = DeviceInfo(
                device_family=device_family,
                device_platform=device_platform,
                device_os=device_os_version,
                device_locale=device_locale,
                app_version=app_version,
                app_build=app_build
            )
            logger.info('Extracted device info: %s' % device_info)
        except Exception as e:
            logger.warning('Device info extract failed due: %s' % e)
            device_info = None
        request.lamb_device_info = device_info
