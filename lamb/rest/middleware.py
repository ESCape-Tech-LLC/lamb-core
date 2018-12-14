# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import warnings

from collections import OrderedDict
from django.conf import settings
from django.http import HttpResponse
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

from lamb.json import JsonResponse
from lamb.exc import *
from lamb.utils import *


# parse http status overriding options
try:
    # backward compatibility
    _should_override_status = settings.LAMB_REST_HTTP_STATUS_ALWAYS_200
    warnings.warn(
        'Use of deprecated settings param LAMB_REST_HTTP_STATUS_ALWAYS_200, use LAMB_RESPONSE_OVERRIDE_STATUS_200 instead',
        DeprecationWarning)
except (ImportError, AttributeError):
    _should_override_status = settings.LAMB_RESPONSE_OVERRIDE_STATUS_200

# parse apps to apply
try:
    # backward compatibility
    _apply_to_apps = settings.LAMB_REST_APPLIED_APPS

    warnings.warn(
        'Use of deprecated settings param LAMB_REST_APPLIED_APPS, use LAMB_RESPONSE_APPLY_TO_APPS instead',
        DeprecationWarning)
except (ImportError, AttributeError):
    _apply_to_apps = settings.LAMB_RESPONSE_APPLY_TO_APPS


logger = logging.getLogger(__name__)


__all__ = [ 'LambRestApiJsonMiddleware' ]


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
        if not isinstance(response, HttpResponse):
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
        if isinstance(exception, (SQLAlchemyError, DBAPIError)):
            status_code = 500
            error_code = LambExceptionCodes.Database
            error_message = 'Database error occurred'
            error_details = None
        elif isinstance(exception, ApiError):
            status_code = exception.status_code
            error_code = exception.app_error_code
            error_message = exception.message
            error_details = exception.error_details
        else:
            status_code = 500
            error_code = LambExceptionCodes.Unknown
            error_message = 'Unknown server side error occurred'
            error_details = None

        # envelope error
        result = OrderedDict()
        result['error_code'] = error_code
        result['error_message'] = error_message
        result['error_details'] = error_details

        # override status if required and return
        if _should_override_status:
            status_code = 200

        return JsonResponse(result, status=status_code, request=request)

    def process_exception(self, request: LambRequest, exception: Exception):
        """ Process expcetion handler """
        return self._process_exception(request=request, exception=exception)
