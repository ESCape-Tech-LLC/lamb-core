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

    @classmethod
    def _trace_id(self, request) -> str:
        if 'HTTP_X_LAMB_TRACEID' in request.META:
            try:
                trace_id = dpath_value(request.META, 'HTTP_X_LAMB_TRACEID', str, transform=transform_uuid)
                logger.debug(f'request trace_id inherited from request header: {trace_id}')
            except Exception as e:
                logger.warning(f'trace_id extract failed: {e}')
                trace_id = uuid.uuid4()
        else:
            trace_id = uuid.uuid4()

        return trace_id

    def _call(self, request) -> HttpResponse:
        request.lamb_trace_id = LambTracingMiddleware._trace_id(request)
        logger.debug(f'request trace_id attached: {request.lamb_trace_id}')
        response = self.get_response(request)
        return response

    async def _acall(self, request) -> HttpResponse:
        request.lamb_trace_id = LambTracingMiddleware._trace_id(request)
        logger.debug(f'request trace_id attached: {request.lamb_trace_id}')
        response = await self.get_response(request)
        return response
