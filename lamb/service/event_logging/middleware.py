import uuid
import logging

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

# Lamb Framework
from lamb.utils import LambRequest, dpath_value
from lamb.utils.transformers import transform_uuid

logger = logging.getLogger(__name__)


__all__ = ["EventLoggingMiddleware"]


class EventLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request: LambRequest):
        """Parse and append event logging trace id and track id to request"""
        # track id parsing
        try:
            # extract info
            track_id = dpath_value(
                request.META, settings.LAMB_EVENT_LOGGING_HEADER_TRACKID, str, default=None, transform=transform_uuid
            )
            logger.debug(f"Extracted track_id for event logging: {track_id}")
        except Exception as e:
            logger.warning(f"track_id extract for event logging failed due to: {e}")
            track_id = None

        if track_id is None:
            track_id = uuid.uuid4()

        request.lamb_track_id = track_id
