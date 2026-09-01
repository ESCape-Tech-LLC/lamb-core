from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
from typing import Any

from django.conf import settings
from django.http import HttpResponse
from django.urls import resolve

from lamb.db.context import lamb_db_context
from lamb.exc import ApiError
from lamb.execution_time import ExecutionTimeMeter
from lamb.execution_time.model import LambExecutionTimeMarker, LambExecutionTimeMetric
from lamb.middleware.base import LambMiddlewareMixin
from lamb.utils import LambRequest, compact, dpath_value
from lamb.utils.core import lazy_default_ro
from lamb.utils.transformers import tf_list_string, transform_boolean
from lamb.utils.validators import v_opt_string

logger = logging.getLogger(__name__)

__all__ = ["LambExecutionTimeMiddleware"]


async_db_writer_queue: asyncio.Queue[LambExecutionTimeMetric] = asyncio.Queue()
async_db_writer_task: asyncio.Task[None] | None = None
async_db_writer_task_init_lock: asyncio.Lock = asyncio.Lock()


class LambExecutionTimeMiddleware(LambMiddlewareMixin):
    """Execution time middleware

    Acting logic:
        - expects that it is not first exception handler in chains - so not processing sync/async `process_exception`
        - so expects that would work over success/not success `HttpResponse` object as response
        - if response object contains hidden field `_lamb_error` produced by `LambRestApiJsonMiddleware` would respect it
        - on start attach `ExecutionTimeMeter` instance to request
        - on finish convert this instance to `LambdaExecutionTimeMetric` object with relevant response/exception status_codes and details
        - collected metric+markers - would be printed in log according to LAMB_EXECUTION_TIME_... settings
        - collected metric+markers - would be stored in database according to LAMB_EXECUTION_TIME_... settings
         # TODO: collect metrics in storage and flush in independent subprocess
         # TODO: respect configuration of percent based log storage in database - reduce count for handbooks, ping...
    """

    sync_capable = True
    async_capable = True

    # settings: memoize
    @lazy_default_ro(default=[])
    def _settings_skip_methods(self) -> list[str]:
        result = dpath_value(settings, "LAMB_EXECUTION_TIME_SKIP_METHODS", str, transform=tf_list_string, default=[])
        result = [r.upper() for r in result]
        logger.debug(f"<{self.__class__.__name__}>. settings_skip_methods: {result}")
        return result

    @lazy_default_ro(default=[])
    def _settings_skip_urls(self) -> list[str]:
        result = dpath_value(settings, "LAMB_EXECUTION_TIME_SKIP_URLS", list, transform=tf_list_string, default=[])
        logger.debug(f"<{self.__class__.__name__}>. settings_skip_log_urls: {result}")
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

        logger.debug(f"<{self.__class__.__name__}>. settings_log_total_level: {result}")
        return result

    @lazy_default_ro(default=None)
    def _settings_log_markers_level(self) -> int | None:
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

        logger.debug(f"<{self.__class__.__name__}>. settings_log_markers_level: {result}")
        return result

    # public contract
    @classmethod
    def append_mark(cls, request: LambRequest, message: str):
        """Appends new marker to request"""
        with contextlib.suppress(Exception):
            request.lamb_execution_meter.append_marker(message)

    # lifecycle
    def __call__(self, request: LambRequest):
        # sync/async adaption
        if self.async_mode:
            return self.__acall__(request)

        # processing
        logger.debug(f"<{self.__class__.__name__}>. Processing __call__")
        self._start(request)

        response = self.get_response(request)
        metric, exception = self._metrics_finalize(request, response)
        self._metrics_log(request=request, metric=metric, response=response, exception=exception)
        self._metrics_store_db(request=request, metric=metric)
        return response

    async def __acall__(self, request: LambRequest):
        # processing
        logger.debug(f"<{self.__class__.__name__}>. Processing __acall__")
        self._start(request)

        response = await self.get_response(request)
        metric, exception = self._metrics_finalize(request, response)
        self._metrics_log(request=request, metric=metric, response=response, exception=exception)
        await self._a_metrics_store_db(request=request, metric=metric)
        return response

    # utilities
    def _start(self, request):
        """Appends metric object to request"""
        request.lamb_execution_meter = ExecutionTimeMeter()
        logger.debug(f"<{self.__class__.__name__}>. start: did attach etm instance")

    def _metrics_finalize(
        self, request: LambRequest, response: HttpResponse | None = None
    ) -> tuple[LambExecutionTimeMetric, Exception | None]:
        """Append finish time mark to internal meter if exists and create corresponding metric record"""
        # auto extract exception info of wellknown forms
        if isinstance(response, HttpResponse) and hasattr(response, "_lamb_error"):
            exception = response._lamb_error
        else:
            exception = None

        # prepare base container and record
        metric = LambExecutionTimeMetric()
        metric.http_method = request.method
        metric.headers = dict(request.headers)
        metric.args = dict(request.GET) or None
        metric.device_info = request.lamb_device_info
        if response is not None:
            metric.status_code = response.status_code
        elif isinstance(exception, ApiError):
            metric.status_code = exception.status_code
        else:
            metric.status_code = None

        # append app_name and url_name
        try:
            resolved = resolve(request.path)
            metric.app_name = resolved.app_name
            metric.url_name = resolved.url_name
        except Exception:  # noqa: S110
            pass

        # finalize meter, collect markers and append context
        try:
            meter = request.lamb_execution_meter

            if meter.context:
                if isinstance(meter.context, list | tuple | set | dict):
                    metric.context = meter.context
                else:
                    logger.warning(
                        f"<{self.__class__.__name__}>. Invalid request.lamb_execution_meter.context value. "
                        f"It will not be saved to DB"
                    )

            meter.append_marker("finish")
            metric.start_time = datetime.datetime.fromtimestamp(meter.start_time)
            metric.elapsed_time = meter.get_total_time()
            if settings.LAMB_EXECUTION_TIME_COLLECT_MARKERS:
                measures = meter.get_measurements()
                for m in measures:
                    marker = LambExecutionTimeMarker()
                    marker.marker = m[0]
                    marker.absolute_interval = m[1]
                    marker.relative_interval = m[2]
                    marker.percentage = m[3]
                    metric.markers.append(marker)
        except Exception:
            logger.exception(f"<{self.__class__.__name__}>. metrics store failed")

        # append exception info
        if exception is not None:
            exc_info: dict[str, Any] = {
                "exc": v_opt_string(str(exception)),
                "exc_cls": str(exception.__class__.__name__),
            }
            if isinstance(exception, ApiError):
                exc_info["app_error_code"] = exception.app_error_code
                if _wrapped := exception.__cause__:
                    exc_info["wrapped"] = {
                        "exc": v_opt_string(str(_wrapped)),
                        "exc_cls": str(_wrapped.__class__.__name__),
                    }
            metric.exc_info = exc_info
        return metric, exception

    def _metrics_log(
        self,
        request: LambRequest,
        metric: LambExecutionTimeMetric,
        response: HttpResponse | None = None,
        exception: Exception | None = None,
    ):
        # log: general info
        if level_total := self._settings_log_total_level:
            components = [
                request.method,
                request.get_full_path(),
                f"{metric.elapsed_time:.6f} sec.",
                metric.status_code,
            ]
            should_log = True
            if response is not None:
                components.append(str(len(response.content)) if not response.streaming else "<streaming>")
                extra = {
                    "status_code": metric.status_code,
                    "streaming": response.streaming,
                    "content_length": len(response.content) if not response.streaming else None,
                }
                if metric.full_name in self._settings_skip_urls:
                    should_log = False
            else:
                components.append(str(exception.__class__.__name__))
                extra = {
                    "status_code": metric.status_code,
                }

            if should_log:
                msg = " ".join(str(r) for r in compact(components))
                logger.log(level_total, msg, extra=extra)

        # log: individual steps
        if level_markers := self._settings_log_markers_level:
            for index, m in enumerate(metric.markers):
                logger.log(level_markers, f"<{self.__class__.__name__}>. [{index}] {m}")

    @classmethod
    async def async_db_writer_worker(cls):
        while True:
            try:
                first_item = await async_db_writer_queue.get()  # would wait until item exist
                batch = [first_item]

                # collect items from queue in batch or until end
                while not async_db_writer_queue.empty() and len(batch) < 500:
                    batch.append(async_db_writer_queue.get_nowait())

                # put info in database
                async with lamb_db_context(pooled=False) as db_session:
                    db_session.add_all(batch)
                    await db_session.commit()
                    logger.debug(f"<{cls.__name__}> async_db_writer_worker. did store batch: {len(batch)}")

                # finally - mark tasks as done
                for _ in batch:
                    async_db_writer_queue.task_done()

            except asyncio.CancelledError:
                logger.info(f"<{cls.__name__}> async_db_writer_worker. Cancelled - breaking")
                break
            except Exception:
                logger.exception(f"<{cls.__name__}> async_db_writer_worker. FAILED -> sleep to let DB restart")
                await asyncio.sleep(5)

    async def _a_metrics_store_db(self, request: LambRequest, metric: LambExecutionTimeMetric):
        global async_db_writer_task

        if async_db_writer_task is None or async_db_writer_task.done():  # call on init/break
            async with async_db_writer_task_init_lock:
                if async_db_writer_task is None or async_db_writer_task.done():  # double check - race condition
                    if async_db_writer_task is None:
                        logger.info(f"<{self.__class__.__name__}>. Starting async DB writer - INITIAL")
                    else:
                        logger.info(f"<{self.__class__.__name__}>. Starting async DB writer - RESTART")

                    loop = asyncio.get_running_loop()
                    async_db_writer_task = loop.create_task(LambExecutionTimeMiddleware.async_db_writer_worker())

        async_db_writer_queue.put_nowait(metric)

    def _metrics_store_db(self, request: LambRequest, metric: LambExecutionTimeMetric):
        if request.method not in self._settings_skip_methods and self._settings_should_store:
            try:
                with lamb_db_context(pooled=settings.LAMB_DB_CONTEXT_POOLED_METRICS) as db_session:
                    db_session.expire_on_commit = False
                    db_session.add(metric)
                    db_session.commit()
                    logger.debug(f"<{self.__class__.__name__}> DB metrics store: [SYNC] SUCCESS")
            except Exception as e:
                logger.error(f"<{self.__class__.__name__}>. DB metrics store: [SYNC] FAILED {e=}")
