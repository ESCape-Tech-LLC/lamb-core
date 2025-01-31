import logging

from django.conf import settings
from django.http import HttpResponse

from lamb.middleware.base import LambMiddlewareMixin

# Lamb Framework
from lamb.utils import LambRequest

__all__ = ["LambCorsMiddleware"]


logger = logging.getLogger(__name__)


class LambCorsMiddleware(LambMiddlewareMixin):

    def after_response(self, request: LambRequest, response: HttpResponse):
        if settings.LAMB_ADD_CORS_ENABLED:
            response["Access-Control-Allow-Origin"] = settings.LAMB_ADD_CORS_ORIGIN
            response["Access-Control-Allow-Methods"] = settings.LAMB_ADD_CORS_METHODS
            response["Access-Control-Allow-Credentials"] = settings.LAMB_ADD_CORS_CREDENTIALS
            response["Access-Control-Allow-Headers"] = ",".join(settings.LAMB_ADD_CORS_HEADERS)
            logger.debug(f"<{self.__class__.__name__}>: adding CORS headers to response")
        return response
