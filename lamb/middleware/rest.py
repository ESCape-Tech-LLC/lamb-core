from __future__ import annotations

import logging
from typing import Any, Tuple
from collections import OrderedDict

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from django.core.exceptions import RequestDataTooBig
from django.utils.deprecation import MiddlewareMixin

# SQLAlchemy
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

# Lamb Framework
from lamb.exc import (
    ApiError,
    ServerError,
    DatabaseError,
    RequestBodyTooBigError,
    ImproperlyConfiguredError,
)
from lamb.json import JsonResponse
from lamb.utils import LambRequest, dpath_value
from lamb.utils.core import import_by_name

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


# TODO: migrate to async/sync version


class LambRestApiJsonMiddleware(MiddlewareMixin):
    """Simple middleware that converts data to JSON.

    1. Looks for all exceptions and converts it to JSON representation
    2. For response that is not subclass of HttpResponse also try to create JsonResponse object
    """

    def process_response(self, request: LambRequest, response: HttpResponse):
        logger.debug(f"<{self.__class__.__name__}>: Processing response")

        """ Process response handler. Also touch request.POST/FILES fields for proper work """
        # touch request body
        _ = request.POST
        _ = request.FILES

        # early return
        if request.resolver_match is None or request.resolver_match.app_name not in _apply_to_apps:
            return response

        # try to encode response
        if not isinstance(response, (HttpResponse, StreamingHttpResponse)):
            try:
                response = JsonResponse(response, request=request)
            except Exception as e:
                response = self.process_exception(request=request, exception=e)

        return response

    _exception_serializer = None

    @classmethod
    def _default_exception_serializer(cls, exception: ApiError) -> Tuple[Any, int]:
        result = OrderedDict()
        result["error_code"] = exception.app_error_code
        result["error_message"] = exception.message
        result["error_details"] = exception.error_details
        return result, exception.status_code

    @classmethod
    def produce_error_response(cls, request: LambRequest, exception: Exception):
        """Internal service for process exception and convert it for proper response info"""
        # touch request body
        _ = request.POST
        _ = request.FILES

        # TODO: check - resolver logic changed
        # early return
        if (_resolver := request.resolver_match) and _resolver.app_name not in _apply_to_apps:
            return exception
        # if request.resolver_match is None or request.resolver_match.app_name not in _apply_to_apps:
        #     return exception

        # process exception to response
        logger.exception("Handled exception:")
        if not isinstance(exception, ApiError):
            if isinstance(exception, _DB_EXCEPTIONS):
                exception = DatabaseError()
            elif isinstance(exception, RequestDataTooBig):
                exception = RequestBodyTooBigError()
            else:
                exception = ServerError()
            logger.error(f"exception wrapped into: {exception!r}")

        # optional patch error
        if settings.LAMB_ERROR_OVERRIDE_PROCESSOR is not None:
            try:
                _processor = import_by_name(settings.LAMB_ERROR_OVERRIDE_PROCESSOR)
                exception = _processor(exception)
            except Exception as e:
                exception = ImproperlyConfiguredError()
                logger.exception("Exception processor failed")
                logger.error(f"Converting {e!r} -> {exception!r}")

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

        result, status_code = cls._exception_serializer(exception)

        if request.method == "HEAD":
            # HEAD requests should not contain any response body
            result = None
        return JsonResponse(result, status=status_code, request=request)

    def process_exception(self, request: LambRequest, exception: Exception):
        """Process exception handler"""
        logger.debug(f"<{self.__class__.__name__}>: Processing exception: {exception}")
        return self.produce_error_response(request=request, exception=exception)
