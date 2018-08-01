# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


import datetime
import logging

from django.core.urlresolvers import resolve
from django.conf import settings

from lamb.execution_time.meter import ExecutionTimeMeter
from lamb.execution_time.model import LambExecutionTimeMetric, LambExecutionTimeMarker

logger = logging.getLogger(__name__)


__all__ = [
    'ExecutionTimeMiddleware'
]


class ExecutionTimeMiddleware(object):

    @classmethod
    def append_mark(cls, request, message):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        :param message: String message to append to marker
        :type message: basestring
        """
        try:
            request.lamb_execution_meter.append_marker(message)
        except: pass

    def _start(self, request):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        """
        request.lamb_execution_meter = ExecutionTimeMeter()

    def _finish(self, request):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        """
        metric = LambExecutionTimeMetric()
        metric.http_method = request.method

        # get execution time
        try:
            time_measure = request.lamb_execution_meter
            time_measure.append_marker('finish')
            metric.start_time = datetime.datetime.fromtimestamp(time_measure.start_time)
            metric.elapsed_time = time_measure.get_total_time()
            if getattr(settings, 'LAMB_EXECUTION_TIME_COLLECT_MARKERS', False):
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
            # logging
            logger.info('Elapsed: %s %s %.6f sec' % (metric.http_method, request.path, metric.elapsed_time))

            # database
            request.lamb_db_session.add(metric)
            request.lamb_db_session.commit()
        except Exception as e:
            logger.error('ExecutionMetrics store error: %s' % e)
            pass



    def process_request(self, request):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        """
        self._start(request)

    def process_response(self, request, response):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        :param response: Response object
        :type response: django.http.HttpResponse
        """
        self._finish(request)
        return response

    def process_exception(self, request, _):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        """
        self._finish(request)
