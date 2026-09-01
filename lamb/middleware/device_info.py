import logging

from lamb.middleware.base import LambMiddlewareMixin
from lamb.types.device_info_type import device_info_factory

logger = logging.getLogger(__name__)


__all__ = ["LambDeviceInfoMiddleware"]


class LambDeviceInfoMiddleware(LambMiddlewareMixin):
    """Middleware parse and append device info and locale to request"""

    sync_capable = True
    async_capable = True

    def before_request(self, request):
        # attach device info
        request.lamb_device_info = device_info_factory(request)
        logger.debug(f"<{self.__class__.__name__}> attached: device_info={request.lamb_device_info}")
