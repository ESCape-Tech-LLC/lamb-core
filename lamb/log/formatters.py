import os
import sys
import datetime
import zoneinfo
import functools
from logging import Formatter, LogRecord

if sys.version_info >= (3, 9):
    from types import GenericAlias

_marker = object()
_default_marker = object()

try:
    from gunicorn.glogging import SafeAtoms
except ImportError:
    SafeAtoms = object()


# Lamb Framework
from lamb.utils import TZ_UTC

from json_log_formatter import JSONFormatter, _json_serializable

__all__ = ["LambFormatter", "LambJSONFormatter"]


class lazy_descriptor:
    """Acts like lazy with default decorator descriptor

    Inspired by lazy package to emulate memoize on success function call, otherwise return default
    """

    def __init__(self, func, default):
        self.__func = func
        self.__default = default
        functools.wraps(self.__func)(self)

    def __set_name__(self, owner, name):
        self.__name__ = name

    def __get__(self, inst, owner):
        if inst is None:
            return self

        if not hasattr(inst, "__dict__"):
            raise AttributeError("'%s' object has no attribute '__dict__'" % (owner.__name__,))

        name = self.__name__
        if name.startswith("__") and not name.endswith("__"):
            name = "_%s%s" % (owner.__name__, name)

        value = inst.__dict__.get(name, _marker)
        if value is _marker:
            try:
                inst.__dict__[name] = value = self.__func(inst)
            except Exception:
                value = self.__default
        return value

    if sys.version_info >= (3, 9):
        __class_getitem__ = classmethod(GenericAlias)


class _TimeFormatMixin:

    # configs
    def _format_time_sep(self) -> str:
        from django.conf import settings

        return settings.LAMB_LOG_FORMAT_TIME_SEP

    format_time_sep = lazy_descriptor(_format_time_sep, "T")

    def _format_time_spec(self) -> str:
        from django.conf import settings

        return settings.LAMB_LOG_FORMAT_TIME_SPEC

    format_time_spec = lazy_descriptor(_format_time_spec, "auto")

    def _timezone(self):
        from django.conf import settings

        return zoneinfo.ZoneInfo(settings.TIME_ZONE)

    timezone = lazy_descriptor(_timezone, TZ_UTC)

    # methods
    def formatTime(self, record: LogRecord, datefmt: str | None = ...) -> str:
        dt = datetime.datetime.fromtimestamp(record.created, tz=self.timezone)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat(sep=self.format_time_sep, timespec=self.format_time_spec)


class LambFormatter(_TimeFormatMixin, Formatter):
    # utils
    def _log_lines_format(self) -> str:
        from django.conf import settings

        return settings.LAMB_LOG_LINES_FORMAT

    log_lines_format = lazy_descriptor(_log_lines_format, "DEFAULT")

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

    def _collect_message(self, record: LogRecord):
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
    def format(self, record: LogRecord) -> str:  # noqa: A003
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


class LambJSONFormatterBase(_TimeFormatMixin, JSONFormatter):
    # utils
    def to_json(self, record):
        # override parent adapt to ascii
        try:
            return self.json_lib.dumps(record, ensure_ascii=False, default=_json_serializable)
        # ujson doesn't support default argument and raises TypeError.
        # "ValueError: Circular reference detected" is raised
        # when there is a reference to object inside the object itself.
        except (TypeError, ValueError, OverflowError):
            try:
                return self.json_lib.dumps(record, ensure_ascii=False)
            except (TypeError, ValueError, OverflowError):
                return "{}"


class LambJSONFormatter(LambJSONFormatterBase):

    # utils
    def to_json(self, record):
        # override parent adapt to ascii
        try:
            return self.json_lib.dumps(record, ensure_ascii=False, default=_json_serializable)
        # ujson doesn't support default argument and raises TypeError.
        # "ValueError: Circular reference detected" is raised
        # when there is a reference to object inside the object itself.
        except (TypeError, ValueError, OverflowError):
            try:
                return self.json_lib.dumps(record, ensure_ascii=False)
            except (TypeError, ValueError, OverflowError):
                return "{}"

    # contract
    # def format(self, record):  # noqa: A003
    #     from django.conf import settings
    #     from django.urls import resolve
    #     from lamb.utils import get_current_request
    #
    #     # combine exception in same message
    #     message = record.getMessage()
    #     if record.exc_info is not None:
    #         message = f"{message}\n{self.formatException(record.exc_info)}"
    #
    #     # main data
    #     data = {
    #         'ts': self.formatTime(record, self.datefmt),
    #         'pid': os.getpid(),
    #         "level": record.levelname,
    #         "msg": message,
    #         "moduleName": record.module,
    #         "fileName": record.filename,
    #         "lineNo": record.lineno,
    #     }
    #
    #     # add status code
    #     status_code = None
    #     try:
    #         status_code = record.status_code
    #     except AttributeError:
    #         if isinstance(record.args, SafeAtoms):
    #             try:
    #                 status_code = int(record.args["s"])
    #             except Exception:
    #                 pass
    #     if status_code is not None:
    #         data["statusCode"] = status_code
    #
    #     # add context
    #     try:
    #         data["context"] = record.context
    #     except AttributeError:
    #         pass
    #
    #     # add specific django info
    #     request = get_current_request()
    #     if request is not None:
    #         data["httpMethod"] = request.method
    #         data["httpUrl"] = request.path
    #
    #         try:
    #             etm = request.lamb_execution_meter
    #             data["elapsedTimeMs"] = round((record.created - etm.start_time) * 1000, 3)
    #         except AttributeError:
    #             pass
    #
    #         try:
    #             data["xray"] = request.xray
    #         except AttributeError:
    #             pass
    #
    #         try:
    #             data["userId"] = request.app_user_id
    #         except Exception:
    #             pass
    #
    #         try:
    #             data["trackId"] = request.lamb_track_id
    #         except AttributeError:
    #             pass
    #
    #         try:
    #             resolved = resolve(request.path)
    #             data["urlName"] = resolved.url_name
    #         except Exception:
    #             pass
    #
    #         for hide_key in settings.LAMB_LOG_JSON_HIDE:
    #             data.pop(hide_key, None)
    #     return self.to_json(data)
