# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import uuid

from django.http import HttpResponse

from lazy import lazy
from lamb import exc
from lamb.utils import dpath_value, get_settings_value
from lamb.utils.transformers import transform_uuid
from lamb.middleware.async_mixin import AsyncMiddlewareMixin

__all__ = ['LambXRayMiddleware']


logger = logging.getLogger(__name__)


class LambXRayMiddleware(AsyncMiddlewareMixin):
    """ Simple middleware that will generate and attach to request trace_id - formatted uuid string """

    @lazy
    def _xray_header(cls):
        logger.info(f'xray header requested')
        try:
            result = get_settings_value(
                'LAMB_LOGGING_HEADER_XRAY',
                'LAMB_EVENT_LOGGING_HEADER_TRACKID',
                req_type=str,
                allow_none=False
            )
            return result
        except exc.ApiError as e:
            raise exc.ImproperlyConfiguredError('X-Ray header config invalid') from e

    @classmethod
    def _xray(self, request) -> str:
        if self._xray_header in request.META:
            try:
                xray = dpath_value(request.META, self._xray_header, str, transform=transform_uuid)
                logger.debug(f'xray inherited from request header: {xray}')
            except Exception as e:
                logger.warning(f'xray extract failed: {e}')
                xray = uuid.uuid4()
        else:
            xray = uuid.uuid4()

        return xray

    def _call(self, request) -> HttpResponse:
        request.xray = LambXRayMiddleware._xray(request)
        logger.debug(f'<{self.__class__.__name__}> Request xray attached: {request.xray}')
        response = self.get_response(request)
        return response

    async def _acall(self, request) -> HttpResponse:
        request.xray = LambXRayMiddleware._xray(request)
        logger.debug(f'<{self.__class__.__name__}> Request xray attached: {request.xray}')
        response = await self.get_response(request)
        return response