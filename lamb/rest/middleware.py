# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import warnings
import uuid
import re

from collections import OrderedDict
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

from lamb.json import JsonResponse
from lamb.exc import *
from lamb.utils import *
from lamb.utils.transformers import transform_uuid


# parse http status overriding options
_should_override_status = settings.LAMB_RESPONSE_OVERRIDE_STATUS_200

# parse apps to apply
_apply_to_apps = settings.LAMB_RESPONSE_APPLY_TO_APPS


logger = logging.getLogger(__name__)


__all__ = ['LambRestApiJsonMiddleware', 'LambTracingMiddleware']


class LambRestApiJsonMiddleware:
    """ Simple middleware that converts data to JSON.

    1. Looks for all exceptions and converts it to JSON representation
    2. For response that is not subclass of HttpResponse also try to create JsonResponse object
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: LambRequest) -> HttpResponse:

        response = self.get_response(request)

        """ Process response handler. Also touchs request.POST/FILES fields for proper work """
        # touch request body
        _ = request.POST
        _ = request.FILES

        # early return if should not catch exception
        if (request.resolver_match is None
                or request.resolver_match.app_name not in _apply_to_apps):
            return response

        # try to encode response
        if not isinstance(response, (HttpResponse, StreamingHttpResponse)):
            try:
                response = JsonResponse(response, request=request)
            except Exception as e:
                response = self._process_exception(request=request, exception=e)

        # override status if required and return
        if _should_override_status:
            response.status_code = 200

        return response

    def _process_exception(self, request: LambRequest, exception: Exception):
        """ Internal service for process exception and convert it for proper response info """
        # early return if should not catch exception
        if (request.resolver_match is None
                or request.resolver_match.app_name not in _apply_to_apps):
            return exception

        # process exception to response
        logger.exception('Handled exception:')
        if not isinstance(exception, ApiError):
            if isinstance(exception, (SQLAlchemyError, DBAPIError)):
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

        # override status if required and return
        if _should_override_status:
            status_code = 200

        return JsonResponse(result, status=status_code, request=request)

    def process_exception(self, request: LambRequest, exception: Exception):
        """ Process expcetion handler """
        return self._process_exception(request=request, exception=exception)


class LambTracingMiddleware(object):
    """ Simple middleware that will generate and attach to request trace_id - formatted uuid string """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: LambRequest) -> HttpResponse:
        if 'HTTP_X_LAMB_TRACEID' in request.META:
            try:
                trace_id = dpath_value(request.META, 'HTTP_X_LAMB_TRACEID', str, transform=transform_uuid)
                logger.debug(f'request trace_id inherited from request header: {trace_id}')
            except Exception as e:
                logger.warning(f'trace_id extract failed: {e}')
                trace_id = uuid.uuid4()
        else:
            trace_id = uuid.uuid4()

        request.lamb_trace_id = str(trace_id).replace('-', '')
        logger.info(f'request trace_id attached: {request.lamb_trace_id}')
        response = self.get_response(request)
        return response
