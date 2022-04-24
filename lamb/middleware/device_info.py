# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from lamb.utils import LambRequest
from lamb.types import LambLocale
from lamb.middleware.async_mixin import AsyncMiddlewareMixin


# from .model import DeviceInfo
from lamb.types.device_info import device_info_factory

logger = logging.getLogger(__name__)


__all__ = [
    'LambDeviceInfoMiddleware'
]


# class LambDeviceInfoMiddleware(MiddlewareMixin):
class LambDeviceInfoMiddleware(AsyncMiddlewareMixin):
    """ Middleware parse and append device info and locale to request """

    def _attach_info(self, request):
        # attach device info
        request.lamb_device_info = device_info_factory(request)
        logger.info(f'lamb device info attached to request: {request.lamb_device_info}')

        # attach device locale
        if request.lamb_device_info.device_locale is not None:
            request.lamb_locale = request.lamb_device_info.device_locale
        else:
            request.lamb_locale = LambLocale.parse(settings.LAMB_DEVICE_DEFAULT_LOCALE)

    def _call(self, request) -> HttpResponse:
        self._attach_info(request)
        response = self.get_response(request)
        return response

    async def _acall(self, request) -> HttpResponse:
        self._attach_info(request)
        response = await self.get_response(request)
        return response
