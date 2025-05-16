from __future__ import annotations

import contextlib
import datetime
import logging

from django.conf import settings
from django.http import HttpResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin

from lamb.db.context import lamb_db_context
from lamb.execution_time import ExecutionTimeMeter
from lamb.execution_time.model import LambExecutionTimeMarker, LambExecutionTimeMetric
from lamb.utils import LambRequest, dpath_value
from lamb.utils.core import lazy_default_ro
from lamb.utils.transformers import tf_list_string, transform_boolean

logger = logging.getLogger(__name__)

__all__ = ["LambExecutionTimeMiddleware"]

# TODO: modify to act like StatsD daemon
# TODO: migrate to async/sync version


class LambExecutionTimeMiddleware(MiddlewareMixin):
    @classmethod
    def append_mark(cls, request: LambRequest, message: str):
        """Appends new marker to request"""
        with contextlib.suppress(Exception):
            request.lamb_execution_meter.append_marker(message)

    # settings: memoize
    @lazy_default_ro(default=[])
    def _settings_skip_methods(self) -> list[str]:
        result = dpath_value(settings, "LAMB_EXECUTION_TIME_SKIP_METHODS", str, transform=tf_list_string, default=[])
        result = [r.upper() for r in result]
        logger.debug(f"<{self.__class__.__name__}>. settings_skip_methods: {result}")
        return result

    @lazy_default_ro(default=False)
    def _settings_should_store(self) -> bool:
        result = dpath_value(settings, "LAMB_EXECUTION_TIME_STORE", str, transform=transform_boolean)
        logger.debug(f"<{self.__class__.__name__}>. settings_should_store: {result}")
        return result

    @lazy_default_ro(default={})
    def _settings_store_rates(self) -> dict[tuple[str, str], float]:
        result = settings.LAMB_EXECUTION_TIME_STORE_RATES
        logger.debug(f"<{self.__class__.__name__}>. settings_store_rates: {result}")
        return result

    @lazy_default_ro(default=None)
    def _settings_log_total_level(self) -> int | None:
        result = settings.LAMB_EXECUTION_TIME_LOG_TOTAL_LEVEL
        if isinstance(result, str):
            result = logging.getLevelName(result.upper())
        elif isinstance(result, int):
            pass
        elif result is None:
            return None
        else:
            logger.warning(f"could not determine LAMB_EXECUTION_TIME_LOG_TOTAL_LEVEL value: {result}")
            raise ValueError

        logger.critical(f"<{self.__class__.__name__}>. settings_log_total_level: {result}")
        return result

    @lazy_default_ro(default=None)
    def _settings_log_markers_level(self) -> int | None:
        logger.critical("looking for: _settings_log_markers_level")
        result = settings.LAMB_EXECUTION_TIME_LOG_MARKERS_LEVEL
        if isinstance(result, str):
            result = logging.getLevelName(result.upper())
        elif isinstance(result, int):
            pass
        elif result is None:
            return None
        else:
            logger.warning(f"could not determine LAMB_EXECUTION_TIME_LOG_MARKERS_LEVEL value: {result}")
            raise ValueError

        logger.critical(f"<{self.__class__.__name__}>. settings_log_markers_level: {result}")
        return result

    # utils
    def _start(self, request):
        """Appends metric object to request"""
        request.lamb_execution_meter = ExecutionTimeMeter()

    def _finish(self, request: LambRequest, response: HttpResponse | None, exception: Exception | None):
        """Stores collected data in database and logs"""
        # prepare base container and record
        metric = LambExecutionTimeMetric()
        metric.http_method = request.method
        metric.headers = dict(request.headers)
        metric.args = dict(request.GET) or None
        metric.device_info = request.lamb_device_info
        metric.status_code = response.status_code if response else None

        # append app_name and url_name
        try:
            resolved = resolve(request.path)
            metric.app_name = resolved.app_name
            metric.url_name = resolved.url_name
        except Exception:
            pass

        # finalize meter, collect markers and append context
        time_measure = None
        try:
            time_measure = request.lamb_execution_meter

            if time_measure.context:
                if isinstance(time_measure.context, list | tuple | set | dict):
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

        # store: database
        if request.method not in self._settings_skip_methods and self._settings_should_store:
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

        # store: logging
        if level_total := self._settings_log_total_level:
            msg = (
                f'"{request.method} {request.get_full_path()}" {request.lamb_execution_meter.get_total_time():.6f} sec.'
            )
            extra = {}
            if response is not None:
                length = len(response.content) if not response.streaming else "<stream>"
                msg = f"{msg} {response.status_code} {length}"
                extra = {
                    "status_code": response.status_code,
                    "streaming": response.streaming,
                    "content_length": len(response.content) if not response.streaming else None,
                }
            elif exception is not None:
                msg = f"{msg} {exception.__class__.__name__}"
                extra = {
                    "status_code": None,
                    "streaming": None,
                    "content_length": None,
                }
            logger.log(level_total, msg, extra=extra)

        logger.critical(f"before check: {self._settings_log_markers_level=} and {time_measure=}")
        if level_markers := self._settings_log_markers_level:
            if time_measure is not None:
                for index, m in enumerate(time_measure.get_log_list()):
                    logger.log(level_markers, f"<{self.__class__.__name__}>. [{index}] {m}")

    # lifecycle
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
