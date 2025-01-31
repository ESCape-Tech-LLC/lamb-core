import contextvars

_request = contextvars.ContextVar("request", default=None)


import logging

from django.http import HttpResponse

# Lamb Framework
from lamb.middleware.base import LambMiddlewareMixin

__all__ = ["LambGRequestMiddleware"]


logger = logging.getLogger(__name__)


class LambGRequestMiddleware(LambMiddlewareMixin):
    """
    Provides storage for the "current" request object, so that code anywhere
    in your project can access it, without it having to be passed to that code
    from the view.

    Drop in replacement for CRequestMiddleware
    """

    def before_request(self, request):
        LambGRequestMiddleware.set_request(request)
        logger.debug(f"<{self.__class__.__name__}>: Did attach request to context")

    def after_response(self, request, response: HttpResponse):
        LambGRequestMiddleware.del_request()
        logger.debug(f"<{self.__class__.__name__}>: Did detach request from context")
        return response

    def process_exception(self, request, exception: Exception):
        LambGRequestMiddleware.del_request()
        logger.debug(f"<{self.__class__.__name__}>: Did detach request from context on exception")

    @classmethod
    def get_request(cls, default=None):
        return _request.get()

    @classmethod
    def set_request(cls, request):
        _request.set(request)

    @classmethod
    def del_request(cls):
        _request.set(None)
