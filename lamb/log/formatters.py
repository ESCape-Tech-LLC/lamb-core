from __future__ import annotations

import os
import json
import logging
import datetime
import zoneinfo
from typing import Any, List, Optional

try:
    from gunicorn.glogging import SafeAtoms
except ImportError:
    SafeAtoms = object()

# Lamb Framework
from lamb.utils.core import masked_dict, lazy_default
from lamb.json.encoder import JsonEncoder
from lamb.log.constants import LAMB_LOG_FORMAT_SIMPLE

__all__ = ["MultilineFormatter", "CeleryMultilineFormatter", "RequestJsonFormatter", "CeleryJsonFormatter"]

# constants
BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",  # TODO: check async/sync mode to add/hide field
    "prefixno",  # in JSON format lamb prefixno not required
    "request",  # django log appends JSON unencodable request object
    # lamb - hide from extra
    "xray",
    "app_user_id",
    "status_code",
}

HTTP_REQUEST_ATTRS = {
    "method": "httpMethod",
    "path": "httpUrl",
    # lamb - add to plain
    "xray": "xray",
    "app_user_id": "userId",
    "lamb_track_id": "trackId",
    "status_code": "statusCode",
}


# utils
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
    @lazy_default("T")
    def sep(self) -> str:
        from django.conf import settings

        return settings.LAMB_LOG_FORMAT_TIME_SEP

    @lazy_default("auto")
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

    def __init__(self, fmt=None, datefmt=None, style="%", validate=True, *, defaults=None):
        if fmt is None:
            fmt = self.default_fmt
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate, defaults=defaults)


class _BaseJsonFormatter(_BaseFormatter):
    """Inspired by [json_log_formatter](https://pypi.org/project/JSON-log-formatter/) project"""

    json_lib = json

    @lazy_default(list())
    def json_hiding_fields(self) -> List[str]:
        from django.conf import settings

        return settings.LAMB_LOG_JSON_HIDE

    @lazy_default(list())
    def extra_masking_keys(self) -> List[str]:
        from django.conf import settings

        return settings.LAMB_LOG_JSON_EXTRA_MASKING

    def to_json(self, record):
        try:
            return self.json_lib.dumps(record, ensure_ascii=False, cls=JsonEncoder)
        # ujson doesn't support default argument and raises TypeError.
        # "ValueError: Circular reference detected" is raised
        # when there is a reference to object inside the object itself.
        except (TypeError, ValueError, OverflowError) as e:
            print(f"level 1 exc: {e}")
            try:
                return self.json_lib.dumps(record, ensure_ascii=False)
            except (TypeError, ValueError, OverflowError) as e:
                try:
                    # everything failed - at least try to provide details
                    msg = {"exc": str(e), "record": str(record)}
                    return self.json_lib.dumps(msg, ensure_ascii=False)
                except Exception as e:
                    print(f"{self.__class__.__name__}. failed encode JSON: record = {record} with exc={e}")
                    return "{}"

    def extra_from_record(self, record):
        """Returns `extra` dict you passed to logger.

        The `extra` keyword argument is used to populate the `__dict__` of
        the `LogRecord`.

        """

        # TODO: modify JSON valid check to better performance version
        # TODO: if would be realized over type lookup - support traverse over list/tuple/dict
        def _json_valid(v) -> Any:
            try:
                json.dumps(v, ensure_ascii=False, cls=JsonEncoder)
                return v
            except Exception:
                return str(v)

        result = {
            attr_name: record.__dict__[attr_name] for attr_name in record.__dict__ if attr_name not in BUILTIN_ATTRS
        }
        result = {k: _json_valid(v) for k, v in result.items()}
        result = masked_dict(result, *self.extra_masking_keys)

        return result

    def json_record(self, message, record):
        """Prepares a JSON payload which will be logged."""
        result = {
            "ts": self.formatTime(record=record, datefmt=self.datefmt),
            "level": record.levelname,
            "pid": os.getpid(),  # TODO: cache ???
            "msg": message,
            "moduleName": record.module,
            "fileName": record.filename,
            "lineNo": record.lineno,
        }

        if record.exc_info:
            result["exc_info"] = self.formatException(record.exc_info)

        # TODO: traverse within extra and check for JSON unencodable with convert to str
        _extra = self.extra_from_record(record)
        if len(_extra) > 0:
            result["extra"] = _extra

        for k in self.json_hiding_fields:
            result.pop(k, None)

        return result

    def format(self, record):  # noqa: A003
        message = record.getMessage()
        json_record = self.json_record(message, record)
        return self.to_json(json_record)


class CeleryMixin:

    @lazy_default(lambda: None)
    def get_current_task(self):
        from celery._state import get_current_task

        return get_current_task

    def format(self, record: logging.LogRecord):  # noqa: A003
        task = self.get_current_task()
        if task and task.request:
            record.__dict__.update(task_id=task.request.id, task_name=task.name)
        else:
            record.__dict__.setdefault("task_name", "")
            record.__dict__.setdefault("task_id", "")
        return super().format(record)


# public formatters
class MultilineFormatter(_BaseFormatter):
    # utils
    @lazy_default("DEFAULT")
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


class CeleryMultilineFormatter(CeleryMixin, MultilineFormatter):
    pass


class RequestJsonFormatter(_BaseJsonFormatter):
    """Subclass of JSON formatter that extracts HTTP request relevant info"""

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
        # Lamb Framework
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


class CeleryJsonFormatter(CeleryMixin, _BaseJsonFormatter):
    pass
