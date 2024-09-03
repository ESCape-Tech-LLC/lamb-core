from __future__ import annotations

import logging
import datetime
from typing import Dict, List, Tuple, Optional

from django.conf import settings
from django.http import HttpResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin

# Lamb Framework
from lamb.utils import LambRequest, dpath_value
from lamb.db.context import lamb_db_context
from lamb.utils.core import lazy
from lamb.execution_time import ExecutionTimeMeter
from lamb.utils.transformers import tf_list_string
from lamb.execution_time.model import LambExecutionTimeMarker, LambExecutionTimeMetric

logger = logging.getLogger(__name__)

__all__ = ["LambExecutionTimeMiddleware"]


class LambExecutionTimeMiddleware(MiddlewareMixin):
    @classmethod
    def append_mark(cls, request: LambRequest, message: str):
        """Appends new marker to request"""
        try:
            request.lamb_execution_meter.append_marker(message)
        except Exception:
            pass

    @lazy
    def skip_methods(self) -> List[str]:
        result = dpath_value(settings, "LAMB_EXECUTION_TIME_SKIP_METHODS", str, transform=tf_list_string, default=[])
        result = [r.upper() for r in result]
        logger.debug(f"<{self.__class__.__name__}>. skip methods: {result}")
        return result

    @lazy
    def store_rates(self) -> Dict[Tuple[str, str], float]:
        result = settings.LAMB_EXECUTION_TIME_STORE_RATES
        return result

    def _start(self, request):
        """Appends metric object to request"""
        request.lamb_execution_meter = ExecutionTimeMeter()

    def _finish(self, request: LambRequest, response: Optional[HttpResponse], exception: Optional[Exception]):
        """Stores collected data in database"""
        metric = LambExecutionTimeMetric()
        metric.http_method = request.method
        metric.headers = dict(request.headers)
        metric.args = dict(request.GET) or None
        metric.device_info = request.lamb_device_info
        metric.status_code = response.status_code if response else None

        # get context and execution time
        try:
            time_measure = request.lamb_execution_meter

            if time_measure.context:
                if isinstance(time_measure.context, (list, tuple, set, dict)):
                    metric.context = time_measure.context
                else:
                    logger.warning(
                        f"<{self.__class__.__name__}>. Invalid request.lamb_execution_meter.context value. "
                        f"It will not be saved to DB"
                    )

            time_measure.append_marker("finish")
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
        except Exception:
            pass

        # get app name and url name
        try:
            resolved = resolve(request.path)
            metric.app_name = resolved.app_name
            metric.url_name = resolved.url_name
        except Exception:
            pass

        # store
        if request.method not in self.skip_methods:
            try:
                # logger.warning(f'analyze store rate: {self.store_rates}')
                # database
                with lamb_db_context(pooled=settings.LAMB_DB_CONTEXT_POOLED_METRICS) as db_session:
                    # make in context to omit invalid commits under exceptions
                    db_session.add(metric)
                    db_session.commit()
            except Exception as e:
                logger.error(f"<{self.__class__.__name__}>. metrics store failed: {e}")
                pass

        # log total
        level = settings.LAMB_EXECUTION_TIME_LOG_TOTAL_LEVEL
        if level:
            if isinstance(level, str):
                # TODO: fix and migrate to mapping - can produce wrong levels if not found
                level = logging.getLevelName(level.upper())
            msg = (
                f'"{request.method} {request.get_full_path()}" {request.lamb_execution_meter.get_total_time():.6f} sec.'
            )
            if response is not None:
                length = len(response.content) if not response.streaming else "<stream>"
                msg = f"{msg} {response.status_code} {length}"
                status_code = response.status_code
            elif exception is not None:
                msg = f"{msg} {exception.__class__.__name__}"
                status_code = None
            logger.log(level, msg, extra={"status_code": status_code})

    def process_request(self, request: LambRequest):
        logger.debug(f"<{self.__class__.__name__}>: Start - attaching etm")
        self._start(request=request)

    def process_response(self, request: LambRequest, response: HttpResponse) -> HttpResponse:
        logger.debug(f"<{self.__class__.__name__}>: Finish on response")
        self._finish(request, response, None)
        return response

    def process_exception(self, request: LambRequest, exception: Exception):
        logger.debug(f"<{self.__class__.__name__}>: Finish on exception")
        self._finish(request, None, exception)
