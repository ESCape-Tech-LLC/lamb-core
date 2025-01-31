import logging

from django.conf import settings

from lamb.middleware.base import LambMiddlewareMixin
from lamb.types.device_info_type import device_info_factory
from lamb.types.locale_type import LambLocale

logger = logging.getLogger(__name__)


__all__ = ["LambDeviceInfoMiddleware"]


class LambDeviceInfoMiddleware(LambMiddlewareMixin):
    """Middleware parse and append device info and locale to request"""

    def before_request(self, request):
        # attach device info
        request.lamb_device_info = device_info_factory(request)
        logger.debug(f"<{self.__class__.__name__}>: Device info attached: {request.lamb_device_info}")

        # attach device locale
        if request.lamb_device_info.device_locale is not None:
            request.lamb_locale = request.lamb_device_info.device_locale
        else:
            request.lamb_locale = LambLocale.parse(settings.LAMB_DEVICE_DEFAULT_LOCALE)
