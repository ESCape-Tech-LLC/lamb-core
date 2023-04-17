import logging

from django.conf import settings
from django.http import HttpResponse

# Lamb Framework
from lamb.types import LambLocale

# from .model import DeviceInfo
from lamb.types.device_info import device_info_factory
from lamb.middleware.async_mixin import AsyncMiddlewareMixin

logger = logging.getLogger(__name__)


__all__ = ["LambDeviceInfoMiddleware"]


# class LambDeviceInfoMiddleware(MiddlewareMixin):
class LambDeviceInfoMiddleware(AsyncMiddlewareMixin):
    """Middleware parse and append device info and locale to request"""

    def _attach_info(self, request):
        # attach device info
        request.lamb_device_info = device_info_factory(request)
        logger.debug(f"<{self.__class__.__name__}>: Device info attached: {request.lamb_device_info}")

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
