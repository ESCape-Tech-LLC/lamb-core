import logging
import uuid

from lamb.middleware.base import LambMiddlewareMixin
from lamb.utils import dpath_value, get_settings_value
from lamb.utils.core import lazy_default_ro
from lamb.utils.transformers import transform_uuid
from lamb.utils.validators import validate_not_empty

__all__ = ["LambXRayMiddleware"]


logger = logging.getLogger(__name__)


class LambXRayMiddleware(LambMiddlewareMixin):
    """
    Simple middleware that will generate and attach to request x-attributes:
    - xray - received from request header or random uuid, aimed to be unique within one web request
    - xline - received from request header or None, aimed to combine several requests under one logical unit
    """

    @lazy_default_ro("X-Lamb-XRay")
    def settings_header_xray(self):
        result = get_settings_value(
            "LAMB_LOG_HEADER_XRAY",
            "LAMB_LOGGING_HEADER_XRAY",
            req_type=str,
            allow_none=False,
            transform=validate_not_empty,
        )
        return result

    @lazy_default_ro("X-Lamb-XLine")
    def settings_header_xline(self):
        result = get_settings_value(
            "LAMB_LOG_HEADER_XLINE",
            "LAMB_EVENT_LOGGING_HEADER_TRACKID",
            req_type=str,
            allow_none=False,
            transform=validate_not_empty,
        )
        return result

    @lazy_default_ro(uuid.NAMESPACE_OID)
    def settings_x_namespace(self):
        result = get_settings_value(
            "LAMB_LOG_XHEADERS_NAMESPACE",
            req_type=str,
            allow_none=False,
            transform=transform_uuid,
        )
        return result

    def _transform_uuid(self, value):
        if isinstance(value, uuid.UUID):
            return value
        value = validate_not_empty(value, min_length=1)

        try:
            return uuid.UUID(value)
        except (TypeError, ValueError) as e:
            result = uuid.uuid5(self.settings_x_namespace, value)
            logger.debug(f"<{self.__class__.__name__}>: telemetry replaced value: [e={e}] {value} -> {result}")
            return result

    def before_request(self, request):
        request.xray = dpath_value(
            request.META,
            self.settings_header_xray,
            str,
            transform=self._transform_uuid,
            default=uuid.uuid4(),
        )
        request.xline = dpath_value(
            request.META,
            self.settings_header_xline,
            str,
            transform=self._transform_uuid,
            default=None,
        )
        logger.debug(
            f"<{self.__class__.__name__}>: Did attach x-fields to request: xray={request.xray}, xline={request.xline}"
        )
