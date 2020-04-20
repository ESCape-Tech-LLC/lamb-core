# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


import datetime
import logging

from django.urls import resolve
from django.conf import settings
from django.http import HttpResponse, HttpRequest
from django.utils.deprecation import MiddlewareMixin

from lamb.execution_time.meter import ExecutionTimeMeter
from lamb.execution_time.model import LambExecutionTimeMetric, LambExecutionTimeMarker
from lamb.utils import *
from lamb.db.context import lamb_db_context

logger = logging.getLogger(__name__)


__all__ = [ 'ExecutionTimeMiddleware' ]


class ExecutionTimeMiddleware(MiddlewareMixin):

    @classmethod
    def append_mark(cls, request: LambRequest, message: str):
        """ Appends new marker to request """
        try:
            request.lamb_execution_meter.append_marker(message)
        except: pass

    def _start(self, request):
        """ Appends metric object to request """
        request.lamb_execution_meter = ExecutionTimeMeter()

    def _finish(self, request: LambRequest, response: HttpResponse, exception: Exception):
        """ Stores collected data in database """
        metric = LambExecutionTimeMetric()
        metric.http_method = request.method

        # get execution time
        try:
            time_measure = request.lamb_execution_meter
            time_measure.append_marker('finish')
            metric.start_time = datetime.datetime.fromtimestamp(time_measure.start_time)
            metric.elapsed_time = time_measure.get_total_time()
            if settings.LAMB_EXECUTION_TIME_COLLECT_MARKERS:
                measures = time_measure.get_measurements()
                for m in measures:
                    marker = LambExecutionTimeMarker()
                    marker.marker = m[0]
                    marker.absolute_interval = m[1]
                    marker.relative_interval = m[2]
                    marker.percentage = m[3]
                    metric.markers.append(marker)
        except: pass

        # get app name and url name
        try:
            resolved = resolve(request.path)
            metric.app_name = resolved.app_name
            metric.url_name = resolved.url_name
        except: pass

        # store
        try:
            # database
            with lamb_db_context() as db_session:
                # make in context to omit invalid commits under exceptions
                db_session.add(metric)
                db_session.commit()
        except Exception as e:
            logger.error('ExecutionMetrics store error: %s' % e)
            pass

        # log total
        level = settings.LAMB_EXECUTION_TIME_LOG_TOTAL_LEVEL
        if level:
            if isinstance(level, str):
                logging.getLogger
                level = logging.mlevel(level)
            msg = f'"{request.method} {request.get_full_path()}" {request.lamb_execution_meter.get_total_time():.6f} sec.'
            if response is not None:
                length = len(response.content) if not response.streaming else '<stream>'
                msg = f'{msg} {response.status_code} {length}'
            elif exception is not None:
                msg = f'{msg} {exception.__class__.__name__}'
            logger.log(level, msg)

    def process_request(self, request: LambRequest):
        self._start(request)

    def process_response(self, request: LambRequest, response: HttpResponse) -> HttpResponse:
        self._finish(request, response, None)
        return response

    def process_exception(self, request: LambRequest, exception: Exception):
        self._finish(request, None, exception)
