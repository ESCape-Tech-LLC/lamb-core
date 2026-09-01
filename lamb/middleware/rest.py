from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.http import HttpResponse, StreamingHttpResponse
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from lamb.exc import ApiError, DatabaseError, ImproperlyConfiguredError, RequestBodyTooBigError, ServerError
from lamb.json import JsonResponse
from lamb.middleware.base import LambMiddlewareMixin
from lamb.utils import LambRequest, compact, dpath_value
from lamb.utils.core import get_full_cls_instance_name, import_by_name

try:
    from cassandra import DriverException
    from cassandra.cluster import NoHostAvailable

    _DB_EXCEPTIONS = (SQLAlchemyError, DBAPIError, DriverException, NoHostAvailable)
except ImportError:
    _DB_EXCEPTIONS = (SQLAlchemyError, DBAPIError)

# parse apps to apply
_apply_to_apps = settings.LAMB_RESPONSE_APPLY_TO_APPS


logger = logging.getLogger(__name__)


__all__ = ["LambRestApiJsonMiddleware"]


class LambRestApiJsonMiddleware(LambMiddlewareMixin):
    """Simple middleware that converts data to JSON.

    Main logic:
        - checks if response should be serialized as JSON according to `LAMB_RESPONSE_APPLY_TO_APPS`
        - in case of exception also converts it to JsonResponse object
        - in case of response next layer is ok, but JSON serialize failed - also convert it to JSON error object
        - usually should be used as last mile middleware
        - in case of success serialization and not streaming response appends `Content-Length` header (Django common middleware not required)
        - also touches request POST/FILES fields to mark it is as respected and omit buffer tmp files error

    TODO: add support for "silent" errors with reduced log level
    """

    async_capable = True
    sync_capable = True

    # protocol: LambMiddlewareMixin sugar
    def after_response(self, request: LambRequest, response: HttpResponse) -> HttpResponse | JsonResponse | Exception:
        """Process successful response from underlying layer"""
        # touch request body
        _ = request.POST
        _ = request.FILES

        # early return
        if request.resolver_match is None or (
            "*" not in _apply_to_apps and request.resolver_match.app_name not in _apply_to_apps
        ):
            return response

        # try to encode response
        if not isinstance(response, HttpResponse | StreamingHttpResponse):
            try:
                response = LambRestApiJsonMiddleware._json_response(data=response, request=request)
            except Exception as e:
                # if serialize to JSON failed - convert this error in valid package
                response = self.produce_error_response(request=request, exception=e)
        elif not response.streaming and not response.has_header("Content-Length"):
            response.headers["Content-Length"] = str(len(response.content))

        return response

    # protocol: django middleware
    def process_exception(self, request: LambRequest, exception: Exception):
        """Process exception from underlying layer"""
        logger.debug(f"<{self.__class__.__name__}>: Processing exception: {exception}")
        return self.produce_error_response(request=request, exception=exception)

    # utils
    _exception_serializer = None

    @classmethod
    def _default_exception_serializer(cls, exception: ApiError, request: LambRequest) -> tuple[Any, int]:
        _ = request  # only for kwarg matching
        result = OrderedDict()
        result["error_code"] = exception.app_error_code
        result["error_message"] = exception.message
        result["error_details"] = exception.error_details
        return result, exception.status_code

    @classmethod
    def produce_error_response(cls, request: LambRequest, exception: Exception, ignore_resolver: bool = False):
        """Public method to produce error response

        - used with internal exception handler
        - can be used with external services/middlewares to produce valid error package
        """
        # touch request body
        _ = request.POST
        _ = request.FILES

        # early return
        if ignore_resolver:
            pass
        elif request.resolver_match is None or (
            "*" not in _apply_to_apps and request.resolver_match.app_name not in _apply_to_apps
        ):
            return exception

        # process exception to response
        if not isinstance(exception, ApiError):
            wrapped_exc = exception
            if isinstance(exception, _DB_EXCEPTIONS):
                exception = DatabaseError()
            elif isinstance(exception, RequestDataTooBig):
                exception = RequestBodyTooBigError()
            else:
                exception = ServerError()

            exception.__cause__ = wrapped_exc
            logger.error(f"<{cls.__name__}> exception wrapped: {exception!r}")

        logger.exception(
            f"<{cls.__name__}> exception handled:",
            extra=compact(
                {
                    "exception_cls": get_full_cls_instance_name(exception),
                    "exception": str(exception),
                    "status_code": exception.status_code if isinstance(exception, ApiError) else None,
                }
            ),
        )

        # envelope error
        if cls._exception_serializer is None:
            if serializer_path := dpath_value(settings, "LAMB_RESPONSE_EXCEPTION_SERIALIZER", str, default=None):
                try:
                    cls._exception_serializer = import_by_name(serializer_path)
                except Exception as e:
                    exception = ImproperlyConfiguredError()
                    logger.exception("Failed to load dynamic serializer -> rolling back to default serializer")
                    logger.error(f"Error occurred: {e!r} -> {exception!r}")
                    cls._exception_serializer = cls._default_exception_serializer
            else:
                cls._exception_serializer = cls._default_exception_serializer

        result, status_code = cls._exception_serializer(exception, request)

        # prepare response
        if request.method == "HEAD":
            # HEAD requests should not contain any response body
            result = None

        response = LambRestApiJsonMiddleware._json_response(data=result, status=status_code, request=request)
        response._lamb_error = exception
        return response

    @staticmethod
    def _json_response(data: Any, request: LambRequest, status: int = 200):
        """Internal utility function
        - converts data to JsonResponse object
        - appends `Content-Length` header
        """
        response = JsonResponse(data, status=status, request=request)
        response.headers["Content-Length"] = str(len(response.content))
        return response
