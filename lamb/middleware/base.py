import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction

from django.http import HttpResponse

__all__ = ["LambMiddlewareMixin"]


logger = logging.getLogger(__name__)


class LambMiddlewareMixin:
    """
    Lamb base middleware aiming to omit context switches in before/after request processing.

    - based on Django MiddlewareMixin but omit context switch penalties
    - handles if applied on class using old-style middlewares
    - use independent before/after logic
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        if get_response is None:
            raise ValueError("get_response must be provided.")
        self.get_response = get_response
        # If get_response is a coroutine function, turns us into async mode so
        # a thread is not consumed during a whole request.
        self.async_mode = iscoroutinefunction(self.get_response)
        if self.async_mode:
            # Mark the class as async-capable, but do the actual switch inside
            # __call__ to avoid swapping out dunder methods.
            markcoroutinefunction(self)

        for m in ["process_request", "process_response", "process_view"]:
            if hasattr(self, m):
                raise ValueError(
                    f"<{self.__class__.__name__}>: could not be used with old style middlewares. "
                    f"Use django.utils.deprecation.MiddlewareMixin instead"
                )

        super().__init__()

    def __repr__(self):
        return "<%s get_response=%s>" % (
            self.__class__.__qualname__,
            getattr(
                self.get_response,
                "__qualname__",
                self.get_response.__class__.__name__,
            ),
        )

    def __call__(self, request) -> HttpResponse:
        # Exit out to async mode, if needed
        logger.debug(f"<{self.__class__.__name__}>: Processing __call__")
        if self.async_mode:
            return self.__acall__(request)
        response = None
        if hasattr(self, "before_request"):
            response = self.before_request(request)
        response = response or self.get_response(request)
        if hasattr(self, "after_response"):
            response = self.after_response(request, response)
        return response

    async def __acall__(self, request) -> HttpResponse:
        # Exit out to async mode, if needed
        logger.debug(f"<{self.__class__.__name__}>: Processing __acall__")
        response = None
        if hasattr(self, "before_request"):
            response = self.before_request(request)
        response = response or await self.get_response(request)
        if hasattr(self, "after_response"):
            response = self.after_response(request, response)
        return response
