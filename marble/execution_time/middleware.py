__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

import datetime

from django.core.urlresolvers import resolve
from django.conf import settings

from marble.execution_time.meter import ExecutionTimeMeter
from marble.execution_time.model import MarbleExecutionTimeMetric, MarbleExecutionTimeMarker


class ExecutionTimeMiddleware(object):

    @classmethod
    def append_mark(cls, request, message):
        """
        :param request: Request object
        :type request: pynm.utils.PYNMRequest
        :param message: String message to append to marker
        :type message: basestring
        """
        try:
            request.marble_execution_meter.append_marker(message)
        except: pass

    def _start(self, request):
        """
        :param request: Request object
        :type request: pynm.utils.PYNMRequest
        """
        request.marble_execution_meter = ExecutionTimeMeter()

    def _finish(self, request):
        """
        :param request: Request object
        :type request: pynm.utils.PYNMRequest
        """
        metric = MarbleExecutionTimeMetric()
        metric.http_method = request.method

        # get execution time
        try:
            time_measure = request.marble_execution_meter
            time_measure.append_marker('finish')
            metric.start_time = datetime.datetime.fromtimestamp(time_measure.start_time)
            metric.elapsed_time = time_measure.get_total_time()
            if getattr(settings, 'MARBLE_EXECUTION_TIME_COLLECT_MARKERS', False):
                measures = time_measure.get_measurements()
                for m in measures:
                    marker = MarbleExecutionTimeMarker()
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
            request.marble_db_session.add(metric)
            request.marble_db_session.commit()
            if settings.DEBUG:
                request.marble_execution_meter.print_marks()
        except: pass


    def process_request(self, request):
        """
        :param request: Request object
        :type request: pynm.utils.PYNMRequest
        """
        self._start(request)

    def process_response(self, request, response):
        """
        :param request: Request object
        :type request: pynm.utils.PYNMRequest
        :param response: Response object
        :type response: django.http.HttpResponse
        """
        self._finish(request)
        return response

    def process_exception(self, request, _):
        """
        :param request: Request object
        :type request: pynm.utils.PYNMRequest
        """
        self._finish(request)