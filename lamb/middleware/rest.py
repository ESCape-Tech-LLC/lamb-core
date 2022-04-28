# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import warnings
import uuid
import re

from collections import OrderedDict

from cassandra import DriverException
from cassandra.cluster import NoHostAvailable
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

from lamb.json import JsonResponse
from lamb.exc import *
from lamb.utils import *
from lamb.utils.transformers import transform_uuid
from lamb.middleware.async_mixin import AsyncMiddlewareMixin


# parse apps to apply
_apply_to_apps = settings.LAMB_RESPONSE_APPLY_TO_APPS


logger = logging.getLogger(__name__)


__all__ = ['LambRestApiJsonMiddleware']


class LambRestApiJsonMiddleware(AsyncMiddlewareMixin):
    """ Simple middleware that converts data to JSON.

    1. Looks for all exceptions and converts it to JSON representation
    2. For response that is not subclass of HttpResponse also try to create JsonResponse object
    """

    def process_response(self, request: LambRequest, response: HttpResponse):
        logger.debug(f'<{self.__class__.__name__}>: Processing response')

        """ Process response handler. Also touch request.POST/FILES fields for proper work """
        # touch request body
        _ = request.POST
        _ = request.FILES

        # early return
        if (request.resolver_match is None
                or request.resolver_match.app_name not in _apply_to_apps):
            return response

        # try to encode response
        if not isinstance(response, (HttpResponse, StreamingHttpResponse)):
            try:
                response = JsonResponse(response, request=request)
            except Exception as e:
                response = self._process_exception(request=request, exception=e)

        return response

    def _process_exception(self, request: LambRequest, exception: Exception):
        """ Internal service for process exception and convert it for proper response info """
        # touch request body
        _ = request.POST
        _ = request.FILES

        # early return
        if (request.resolver_match is None
                or request.resolver_match.app_name not in _apply_to_apps):
            return exception

        # process exception to response
        logger.exception('Handled exception:')
        if not isinstance(exception, ApiError):
            if isinstance(exception, (SQLAlchemyError, DBAPIError, NoHostAvailable, DriverException)):
                exception = DatabaseError()
            else:
                exception = ServerError()
            logger.error(f'exception wrapped into: {exception!r}')

        # optional patch error
        if settings.LAMB_ERROR_OVERRIDE_PROCESSOR is not None:
            try:
                _processor = import_by_name(settings.LAMB_ERROR_OVERRIDE_PROCESSOR)
                exception = _processor(exception)
            except Exception as e:
                exception = ImproperlyConfiguredError()
                logger.exception(f'Exception processor failed')
                logger.error(f'Converting {e!r} -> {exception!r}')

        # envelope error
        result = OrderedDict()
        status_code = exception.status_code
        result['error_code'] = exception.app_error_code
        result['error_message'] = exception.message
        result['error_details'] = exception.error_details

        return JsonResponse(result, status=status_code, request=request)

    def process_exception(self, request: LambRequest, exception: Exception):
        """ Process exception handler """
        logger.debug(f'<{self.__class__.__name__}>: Processing exception: {exception}')
        return self._process_exception(request=request, exception=exception)
