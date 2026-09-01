import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.http import HttpResponse

from lamb.exc import ProgrammingError

__all__ = ["LambMiddlewareMixin"]


logger = logging.getLogger(__name__)


class LambMiddlewareMixin:
    """
    Lamb base middleware aiming to omit context switches in before/after request processing.

    Main logic:
        - checks if applied to old-style middlewares looking for methods `process_request`, `process_response` and `process_view` - would raise Exception in this case
        - desired to support both sync and async modes to reduce context switches
        - during django init step analyze is next layer is coroutine - in this case mark self as coroutine function
        - during execution step analyze is act in async mode and in this case - switch to async call version
        - provides independent sugar methods for children class to not implement custom __call__/__acall__ methods
        - sugar methods `before_request`, `after_response` - should not use IO bound calls to not break context switches
        - exception in underlying layers should be processed with classic `process_exception` method

    NOTE: `process_exception` in case of async/sync IO bound operations required - could be complex task
        - option 1: inspect hidden _lamb_error - like `LambExecutionTimeMiddleware`
        - option 2: implement fully customized __call__/__acall__ method and may be even switch `process_response` in __init__ like

        def __init__(self, get_response):
            super().__init__(get_response)
            if self.async_mode:
                self.process_exception = self.process_exception_async
            else:
                self.process_exception = self.process_exception_sync
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        # checks
        if get_response is None:
            raise ValueError("get_response must be provided.")

        for m in ["process_request", "process_response", "process_view"]:
            if hasattr(self, m):
                raise ProgrammingError(
                    f"<{self.__class__.__name__}>: could not be used with old style middlewares. "
                    f"Use django.utils.deprecation.MiddlewareMixin instead"
                )

        # construct and analyse next layer
        self.get_response = get_response
        # If next layer is async function
        # - turn self into async mode - would be respected in call
        # - mark self as async function - to force django respect it in context switch chain
        self.async_mode = iscoroutinefunction(self.get_response)
        if self.async_mode:
            # Mark the class intself as async-capable, but do the actual switch inside
            # __call__ to avoid swapping out dunder methods.
            markcoroutinefunction(self)

    def __repr__(self):
        return "<{} get_response={}>".format(
            self.__class__.__qualname__,
            getattr(
                self.get_response,
                "__qualname__",
                self.get_response.__class__.__name__,
            ),
        )

    def __call__(self, request) -> HttpResponse:
        # Actually django in all cases invokes methods __call__
        # - in sync mode - it is called as sync function `res = m(request)`
        # - in async mode - it is called as async function `res = await m(request)`
        # - so monkeypatch is easy - we understand our mode and in async mode returns async version
        # Exit out to async mode, if needed
        if self.async_mode:
            return self.__acall__(request)

        # processing
        logger.debug(f"<{self.__class__.__name__}>: Processing __call__")
        response = None
        if hasattr(self, "before_request"):
            response = self.before_request(request)

        response = response or self.get_response(request)

        if hasattr(self, "after_response"):
            response = self.after_response(request, response)
        return response

    async def __acall__(self, request) -> HttpResponse:
        logger.debug(f"<{self.__class__.__name__}>: Processing __acall__")
        response = None
        if hasattr(self, "before_request"):
            response = self.before_request(request)

        response = response or await self.get_response(request)

        if hasattr(self, "after_response"):
            response = self.after_response(request, response)
        return response
