import contextvars

_request = contextvars.ContextVar("request", default=None)


import logging

from django.http import HttpResponse

# Lamb Framework
from lamb.middleware.async_mixin import AsyncMiddlewareMixin

__all__ = ["LambGRequestMiddleware"]


logger = logging.getLogger(__name__)


class LambGRequestMiddleware(AsyncMiddlewareMixin):
    """
    Provides storage for the "current" request object, so that code anywhere
    in your project can access it, without it having to be passed to that code
    from the view.

    Drop in replacement for CRequestMiddleware
    """

    def _call(self, request) -> HttpResponse:
        logger.debug(f"<{self.__class__.__name__}>: Attaching request to context")
        self.__class__.set_request(request)
        response = self.get_response(request)
        logger.debug(f"<{self.__class__.__name__}>: Detaching request from context")
        self.__class__.del_request()
        return response

    async def _acall(self, request) -> HttpResponse:
        logger.debug(f"<{self.__class__.__name__}>: Attaching request to context")
        self.__class__.set_request(request)
        response = await self.get_response(request)
        logger.debug(f"<{self.__class__.__name__}>: Detaching request from context")
        self.__class__.del_request()
        return response

    @classmethod
    def get_request(cls, default=None):
        return _request.get()

    @classmethod
    def set_request(cls, request):
        _request.set(request)

    @classmethod
    def del_request(cls):
        _request.set(None)
