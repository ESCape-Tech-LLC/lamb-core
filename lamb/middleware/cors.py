# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import asyncio

from django.conf import settings
from django.http import HttpResponse

from lamb.middleware.async_mixin import AsyncMiddlewareMixin

__all__ = ['LambCorsMiddleware']


logger = logging.getLogger(__name__)


class LambCorsMiddleware(AsyncMiddlewareMixin):

    def process_response(self, _, response: HttpResponse) -> HttpResponse:
        if settings.LAMB_ADD_CORS_ENABLED:
            response['Access-Control-Allow-Origin'] = settings.LAMB_ADD_CORS_ORIGIN
            response['Access-Control-Allow-Methods'] = settings.LAMB_ADD_CORS_METHODS
            response['Access-Control-Allow-Credentials'] = settings.LAMB_ADD_CORS_CREDENTIALS
            response['Access-Control-Allow-Headers'] = ','.join(settings.LAMB_ADD_CORS_HEADERS)
            logger.warning(f'adding CORS headers to response')
        return response
