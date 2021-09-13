# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from lamb.utils import LambRequest
from lamb.types import LambLocale


# from .model import DeviceInfo
from lamb.types.device_info import device_info_factory

logger = logging.getLogger(__name__)


__all__ = [
    'DeviceInfoMiddleware'
]


class DeviceInfoMiddleware(MiddlewareMixin):

    def process_request(self, request: LambRequest):
        """ Middleware parse and append device info and locale to request """
        # attach device info
        request.lamb_device_info = device_info_factory(request)
        logger.warning(f'lamb device info attached to request: {request.lamb_device_info}')

        # attach device locale
        if request.lamb_device_info.device_locale is not None:
            request.lamb_locale = request.lamb_device_info.device_locale
        else:
            request.lamb_locale = LambLocale.parse(settings.LAMB_DEVICE_DEFAULT_LOCALE)
