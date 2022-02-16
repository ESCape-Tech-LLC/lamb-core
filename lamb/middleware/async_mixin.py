# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import asyncio
import logging

from django.http import HttpResponse

__all__ = ['AsyncMiddlewareMixin']


logger = logging.getLogger(__name__)


class AsyncMiddlewareMixin:
    """
    Syntax sugar for class based sync/async compatible middleware:

        - based on Django MiddlewareMixin but omit context switch penalties
        - provides flexible way to override sync/async processing
        - for trivial scenarios support process_response(response) signature for final processing
    """
    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        if get_response is None:
            raise ValueError('get_response must be provided.')
        self.get_response = get_response
        self._async_check()
        super().__init__()

    def __repr__(self):
        return '<%s get_response=%s>' % (
            self.__class__.__qualname__,
            getattr(
                self.get_response,
                '__qualname__',
                self.get_response.__class__.__name__,
            ),
        )

    def _async_check(self):
        """
        If get_response is a coroutine function, turns us into async mode so
        a thread is not consumed during a whole request.
        """
        if asyncio.iscoroutinefunction(self.get_response):
            # Mark the class as async-capable, but do the actual switch
            # inside __call__ to avoid swapping out dunder methods
            self._is_coroutine = asyncio.coroutines._is_coroutine
            logger.info(f'{self}. _async_check -> async -> _is_coroutine{self._is_coroutine}')
        else:
            logger.info(f'{self}. _async_check -> sync')

    def __call__(self, request):
        # Exit out to async mode, if needed
        if asyncio.iscoroutinefunction(self.get_response):
            logger.warning(f'{self}. Running mode: ASYNC')
            return self._acall(request)
        else:
            logger.warning(f'{self}. Running mode: SYNC')
            return self._call(request)

    def _call(self, request) -> HttpResponse:
        response = self.get_response(request)
        if hasattr(self, 'process_response'):
            response = self.process_response(response)
        return response

    async def _acall(self, request) -> HttpResponse:
        response = await self.get_response(request)
        if hasattr(self, 'process_response'):
            response = self.process_response(response)
        return response
