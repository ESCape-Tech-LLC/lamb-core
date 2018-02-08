__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

import logging
from collections import OrderedDict

from django.conf import settings
from django.core.urlresolvers import resolve, Resolver404
from django.http import HttpResponse
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

from lamb.json import JsonResponse
from lamb.rest.exceptions import *

apply_to_apps = getattr(settings, 'LAMB_REST_APPLIED_APPS', [])

logger = logging.getLogger(__name__)

__all__ = [
    'LambRestApiJsonMiddleware'
]

class LambRestApiJsonMiddleware(object):
    """ Simple middleware that converts data to JSON.

    1. Looks for all exceptions and converts it to JSON representation
    2. For response that is not subclass of HttpResponse also try to create JsonResponse object
    """

    def _process_exception(self, request, exception):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        :param exception: Exception object
        :type exception: Exception
        """
        # return if should nto catch exception
        try:
            if resolve(request.path).app_name not in apply_to_apps:
                return exception
        except Resolver404:
            return exception

        # process exception to response
        logger.exception("Handled exception: ")
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

        result = OrderedDict()
        result['error_code'] = error_code
        result['error_message'] = error_message
        result['error_details'] = error_details

        return JsonResponse(result, status=status_code, request=request)

    def process_response(self, request, response):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        :param response: Response object
        :type response: django.http.HttpResponse
        """
        # touch request params
        _ = request.POST
        _ = request.FILES
        try:
            if resolve(request.path).app_name not in apply_to_apps:
                return response
        except Resolver404:
            return response

        if not isinstance(response, HttpResponse):
            try:
                response = JsonResponse(response, request=request)
            except Exception as e:
                return self._process_exception(request=request, exception=e)

        return response

    def process_exception(self, request, exception):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        :param exception: Exception object
        :type exception: Exception
        """
        return self._process_exception(request=request, exception=exception)