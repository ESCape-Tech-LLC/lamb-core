import uuid
import logging

from django.http import HttpResponse

# Lamb Framework
from lamb import exc
from lamb.utils import dpath_value, get_settings_value
from lamb.utils.transformers import transform_uuid
from lamb.middleware.async_mixin import AsyncMiddlewareMixin

from lazy import lazy

__all__ = ["LambXRayMiddleware"]


logger = logging.getLogger(__name__)


class LambXRayMiddleware(AsyncMiddlewareMixin):
    """Simple middleware that will generate and attach to request trace_id - formatted uuid string"""

    _xray_header = None

    @classmethod
    @property
    def xray_header(cls):
        if cls._xray_header is None:
            logger.info(f"<{cls.__name__}>. xray header requested")
            try:
                cls._xray_header = get_settings_value(
                    "LAMB_LOGGING_HEADER_XRAY", "LAMB_EVENT_LOGGING_HEADER_TRACKID", req_type=str, allow_none=False
                )
            except exc.ApiError:
                logger.info(
                    f"LAMB_LOGGING_HEADER_XRAY config is required for LambXRayMiddleware using. "
                    f"Will use default HTTP_X_LAMB_XRAY value"
                )
                cls._xray_header = "HTTP_X_LAMB_XRAY"
        return cls._xray_header

    @classmethod
    def _xray(cls, request) -> str:
        if cls.xray_header in request.META:
            try:
                xray = dpath_value(request.META, cls.xray_header, str, transform=transform_uuid)
                logger.debug(f"<{cls.__name__}>. xray inherited from request header: {xray}")
            except Exception as e:
                logger.warning(f"<{cls.__name__}>. xray extract failed: {e}")
                xray = uuid.uuid4()
        else:
            xray = uuid.uuid4()

        return xray

    def _call(self, request) -> HttpResponse:
        request.xray = LambXRayMiddleware._xray(request)
        logger.debug(f"<{self.__class__.__name__}>. request xray attached: {request.xray}")
        response = self.get_response(request)
        return response

    async def _acall(self, request) -> HttpResponse:
        request.xray = LambXRayMiddleware._xray(request)
        logger.debug(f"<{self.__class__.__name__}>. request xray attached: {request.xray}")
        response = await self.get_response(request)
        return response
