# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import uuid

from django.conf import settings
from django.http import HttpResponse

from lamb.utils import dpath_value, LambRequest
from lamb.utils.transformers import transform_uuid
from lamb.middleware.async_mixin import AsyncMiddlewareMixin

__all__ = ['LambTracingMiddleware']


logger = logging.getLogger(__name__)


class LambTracingMiddleware(AsyncMiddlewareMixin):
    """ Simple middleware that will generate and attach to request trace_id - formatted uuid string """

    # def __init__(self, get_response):
    #     self.get_response = get_response

    # def __call__(self, request: LambRequest) -> HttpResponse:
    #     if 'HTTP_X_LAMB_TRACEID' in request.META:
    #         try:
    #             trace_id = dpath_value(request.META, 'HTTP_X_LAMB_TRACEID', str, transform=transform_uuid)
    #             logger.debug(f'request trace_id inherited from request header: {trace_id}')
    #         except Exception as e:
    #             logger.warning(f'trace_id extract failed: {e}')
    #             trace_id = uuid.uuid4()
    #     else:
    #         trace_id = uuid.uuid4()
    #
    #     request.lamb_trace_id = str(trace_id).replace('-', '')
    #     logger.debug(f'request trace_id attached: {request.lamb_trace_id}')
    #     response = self.get_response(request)
    #     return response

    def _call(self, request) -> HttpResponse:
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
        logger.debug(f'request trace_id attached: {request.lamb_trace_id}')
        response = self.get_response(request)
        return response

        # request.lamb_trace_id = str(trace_id).replace('-', '')
        # logger.debug(f'request trace_id attached: {request.lamb_trace_id}')
        # pass

    async def _acall(self, request) -> HttpResponse:
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
        logger.debug(f'request trace_id attached: {request.lamb_trace_id}')
        response = await self.get_response(request)
        return response
        # pass
