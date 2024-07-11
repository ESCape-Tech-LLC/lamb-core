import os
import logging
import datetime
import zoneinfo
import json
from typing import Union, Optional, List
from lamb.utils.core import lazy_default

try:
    from gunicorn.glogging import SafeAtoms
except ImportError:
    SafeAtoms = object()

# Lamb Framework
from lamb.utils import TZ_UTC
from lamb.log.constants import LAMB_LOG_FORMAT_SIMPLE, LAMB_LOG_FORMAT_CELERY_MAIN_SIMPLE, LAMB_LOG_FORMAT_CELERY_TASK_SIMPLE
from json_log_formatter import JSONFormatter, _json_serializable

__all__ = ["LambFormatter", "LambJSONFormatter", 'MultilineFormatter', 'CeleryMultilineFormatter']


class _BaseFormatter(logging.Formatter):
    """
    Lamb base formatter used to convert LogRecord to text.

    Aimed to provide configurable LogRecord created time text representation according to ISO specification.
    Separator, timespec and timezone params for logs by default extracted from django conf with lazy_descriptor,
    that give several abilities:
    - usage of default values in descriptors act as last mile until django settings is loaded
    - descriptors provide ability to modify values on instance level and on class level
    """

    default_fmt = LAMB_LOG_FORMAT_SIMPLE

    # on logger start django settings could not be initialized
    # use memoized with default descriptors
    @lazy_default('T')
    def sep(self) -> str:
        from django.conf import settings
        return settings.LAMB_LOG_FORMAT_TIME_SEP

    @lazy_default('auto')
    def timespec(self) -> str:
        from django.conf import settings

        return settings.LAMB_LOG_FORMAT_TIME_SPEC

    @lazy_default(None)
    def tzinfo(self) -> Optional[datetime.tzinfo]:
        from django.conf import settings

        timezone_name = settings.LAMB_LOG_FORMAT_TIME_ZONE
        if timezone_name is None:
            return None
        try:
            return zoneinfo.ZoneInfo(timezone_name)
        except Exception as e:
            # to stop lazy cycle on config resolved
            print(f"failed to load timezone: {e}")
            return None

    # contract
    def formatTime(self, record, datefmt: Optional[str] = ...) -> str:
        ct = datetime.datetime.fromtimestamp(record.created, tz=self.tzinfo)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.isoformat(sep=self.sep, timespec=self.timespec)

        return s

    def __init__(self, fmt=None, datefmt=None, style='%', validate=True, *,
                 defaults=None):
        if fmt is None:
            fmt = self.default_fmt
            # fmt = LAMB_LOG_FORMAT_SIMPLE
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate, defaults=defaults)


BUILTIN_ATTRS = {
    'args',
    'asctime',
    'created',
    'exc_info',
    'exc_text',
    'filename',
    'funcName',
    'levelname',
    'levelno',
    'lineno',
    'module',
    'msecs',
    'message',
    'msg',
    'name',
    'pathname',
    'process',
    'processName',
    'relativeCreated',
    'stack_info',
    'thread',
    'threadName',
    'taskName',
    'prefixno',
    'request'
}


class BaseJsonFormatter(_BaseFormatter):
    """ Inspired by [json_log_formatter](https://pypi.org/project/JSON-log-formatter/) project """

    json_lib = json

    @lazy_default(list())
    def json_hiding_fields(self) -> List[str]:
        from django.conf import settings
        return settings.LAMB_LOG_JSON_HIDE

    def to_json(self, record):
        try:
            return self.json_lib.dumps(record, ensure_ascii=False, default=_json_serializable,)
        # ujson doesn't support default argument and raises TypeError.
        # "ValueError: Circular reference detected" is raised
        # when there is a reference to object inside the object itself.
        except (TypeError, ValueError, OverflowError):
            try:
                return self.json_lib.dumps(record, ensure_ascii=False)
            except (TypeError, ValueError, OverflowError) as e:
                print(f'last barrier: {e} -> {record}')
                return '{}'

    def extra_from_record(self, record):
        """Returns `extra` dict you passed to logger.

        The `extra` keyword argument is used to populate the `__dict__` of
        the `LogRecord`.

        """
        return {
            attr_name: record.__dict__[attr_name]
            for attr_name in record.__dict__
            if attr_name not in BUILTIN_ATTRS
        }

    def json_record(self, message, record):
        """ Prepares a JSON payload which will be logged."""
        result = {
            'ts': self.formatTime(record=record, datefmt=self.datefmt),
            'level': record.levelname,
            'pid': os.getpid(),  # TODO: cache ???
            'msg': message,
            'moduleName': record.module,
            'fileName': record.filename,
            'lineNo': record.lineno,
        }

        if record.exc_info:
            result['exc_info'] = self.formatException(record.exc_info)

        result.update(self.extra_from_record(record))

        for k in self.json_hiding_fields:
            result.pop(k, None)

        return result

    def format(self, record):
        message = record.getMessage()
        json_record = self.json_record(message, record)
        return self.to_json(json_record)


class MultilineFormatter(_BaseFormatter):
    # utils
    @lazy_default('DEFAULT')
    def log_lines_format(self):
        from django.conf import settings

        return settings.LAMB_LOG_LINES_FORMAT

    def _format_message_prefix(self, record):
        buffer = record.message.split("\n")
        paths = []
        for index, message_part in enumerate(buffer):
            record.message = message_part
            record.prefixno = index + 1
            paths.append(self._style.format(record))
        return "\n".join(paths)

    def _format_message_single(self, record):
        result = self._style.format(record)
        return result.replace("\n", " ")

    def _format_message_default(self, record):
        return self._style.format(record)

    def _collect_message(self, record: logging.LogRecord):
        message = record.getMessage()
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if message[-1:] != "\n":
                message = message + "\n"
            message = message + record.exc_text
        if record.stack_info:
            if message[-1:] != "\n":
                message = message + "\n"
            message = message + self.formatStack(record.stack_info)
        return message

    # contract
    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        record.message = self._collect_message(record)

        match self.log_lines_format:
            case "DEFAULT":
                return self._format_message_default(record)
            case "PREFIX":
                return self._format_message_prefix(record)
            case "SINGLE_LINE":
                return self._format_message_single(record)
            case _:
                raise ValueError(f"Unknown log line format: {self.log_lines_format}")


class CeleryMixin:

    @lazy_default(lambda: None)
    def get_current_task(self):
        from celery._state import get_current_task

        return get_current_task

    def format(self, record: logging.LogRecord):
        task = self.get_current_task()
        if task and task.request:
            record.__dict__.update(task_id=task.request.id, task_name=task.name)
        else:
            record.__dict__.setdefault("task_name", "")
            record.__dict__.setdefault("task_id", "")
        return super().format(record)


class CeleryMultilineFormatter(CeleryMixin, MultilineFormatter):
    pass


LambFormatter = MultilineFormatter


HTTP_REQUEST_ATTRS = {
    'method': 'httpMethod',
    'path': 'httpUrl',
    'xray': 'xray',
    'lamb_track_id': 'trackId',
}


class RequestJsonFormatter(BaseJsonFormatter):

    def json_record(self, message, record):
        from django.urls import resolve
        result = super().json_record(message, record)

        # append status code
        status_code = None
        try:
            status_code = record.status_code
        except AttributeError:
            if isinstance(record.args, SafeAtoms):
                try:
                    status_code = int(record.args["s"])
                except Exception:
                    pass
        if status_code is not None:
            result["statusCode"] = status_code

        # request info
        from lamb.utils import get_current_request
        request = get_current_request()

        if request is not None:
            request_attrs = {
                json_name: request.__dict__[attr_name]
                for attr_name, json_name in HTTP_REQUEST_ATTRS.items()
                if attr_name in request.__dict__
            }
            result.update(request_attrs)

            try:
                etm = request.lamb_execution_meter
                result["elapsedTimeMs"] = round((record.created - etm.start_time) * 1000, 3)
            except AttributeError:
                pass

            try:
                resolved = resolve(request.path)
                result["urlName"] = resolved.url_name
            except Exception:
                pass

        return result


LambJSONFormatter = RequestJsonFormatter

class CeleryJsonFormatter(CeleryMixin, BaseJsonFormatter):
    pass
# class LambJSONFormatter(BaseJsonFormatter):
#     pass
# class LambJSONFormatter(_LambJSONFormatterBase):
#
#     # utils
#     def to_json(self, record):
#         # override parent adapt to ascii
#         try:
#             return self.json_lib.dumps(record, ensure_ascii=False, default=_json_serializable)
#         # ujson doesn't support default argument and raises TypeError.
#         # "ValueError: Circular reference detected" is raised
#         # when there is a reference to object inside the object itself.
#         except (TypeError, ValueError, OverflowError):
#             try:
#                 return self.json_lib.dumps(record, ensure_ascii=False)
#             except (TypeError, ValueError, OverflowError):
#                 return "{}"
#
#     # contract
#     def _format(self, record):  # noqa: A003
#         from django.conf import settings
#         from django.urls import resolve
#
#         # Lamb Framework
#         from lamb.utils import get_current_request
#
#         # combine exception in same message
#         message = record.getMessage()
#         if record.exc_info is not None:
#             message = f"{message}\n{self.formatException(record.exc_info)}"
#
#         # main data
#         data = {
#             "ts": self.formatTime(record, self.datefmt),
#             "pid": os.getpid(),
#             "level": record.levelname,
#             "msg": message,
#             "moduleName": record.module,
#             "fileName": record.filename,
#             "lineNo": record.lineno,
#         }
#
#         # add status code
#         status_code = None
#         try:
#             status_code = record.status_code
#         except AttributeError:
#             if isinstance(record.args, SafeAtoms):
#                 try:
#                     status_code = int(record.args["s"])
#                 except Exception:
#                     pass
#         if status_code is not None:
#             data["statusCode"] = status_code
#
#         # add context
#         try:
#             data["context"] = record.context
#         except AttributeError:
#             pass
#
#         # add specific django info
#         request = get_current_request()
#         if request is not None:
#             data["httpMethod"] = request.method
#             data["httpUrl"] = request.path
#
#             try:
#                 etm = request.lamb_execution_meter
#                 data["elapsedTimeMs"] = round((record.created - etm.start_time) * 1000, 3)
#             except AttributeError:
#                 pass
#
#             try:
#                 data["xray"] = request.xray
#             except AttributeError:
#                 pass
#
#             try:
#                 data["userId"] = request.app_user_id
#             except Exception:
#                 pass
#
#             try:
#                 data["trackId"] = request.lamb_track_id
#             except AttributeError:
#                 pass
#
#             try:
#                 resolved = resolve(request.path)
#                 data["urlName"] = resolved.url_name
#             except Exception:
#                 pass
#
#             for hide_key in settings.LAMB_LOG_JSON_HIDE:
#                 data.pop(hide_key, None)
#         return self.to_json(data)
