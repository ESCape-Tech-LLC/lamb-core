import os
import time

# from logging import Formatter, LogRecord
import logging
import datetime
import zoneinfo
from typing import Union, Optional

# Lamb Framework
from lamb.utils.core import lazy_descriptor

try:
    from gunicorn.glogging import SafeAtoms
except ImportError:
    SafeAtoms = object()


# Lamb Framework
from lamb.utils import TZ_UTC

from json_log_formatter import JSONFormatter, _json_serializable

__all__ = ["LambFormatter", "LambJSONFormatter"]


from lazy import lazy


class _BaseFormatter(logging.Formatter):
    """
    Lamb base formatter used to convert LogRecord to text.

    Aimed to provide configurable LogRecord created time text representation according to ISO specification.
    Separator, timespec and timezone params for logs by default extracted from django conf with lazy_descriptor,
    that give several abilities:
    - usage of default values in descriptors act as last mile until django settings is loaded
    - descriptors provide ability to modify values in instance level and on class level
    """

    _sep: str = "T"
    _spec: str = "auto"
    _tz: Optional[datetime.tzinfo] = None

    # memoize
    def _sep(self) -> str:
        from django.conf import settings

        return settings.LAMB_LOG_FORMAT_TIME_SEP

    sep: str = lazy_descriptor(_sep, "T")

    def _timespec(self) -> str:
        from django.conf import settings

        return settings.LAMB_LOG_FORMAT_TIME_SPEC

    timespec: str = lazy_descriptor(_timespec, "auto")

    def _tzinfo(self) -> Optional[datetime.tzinfo]:
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

    tzinfo: datetime.tzinfo = lazy_descriptor(_tzinfo, None)

    # contract
    def formatTime(self, record, datefmt: Optional[str] = ...) -> str:
        print(f"formatTime invoked: {self.sep, self.timespec, self.tzinfo}")
        ct = datetime.datetime.fromtimestamp(record.created, tz=self.tzinfo)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.isoformat(sep=self.sep, timespec=self.timespec)

        return s


# mixins
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
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = ...) -> str:
        dt = datetime.datetime.fromtimestamp(record.created, tz=self.timezone)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat(sep=self.format_time_sep, timespec=self.format_time_spec)


class _LambJSONFormatterBase(_TimeFormatMixin, JSONFormatter):

    def _hide_atoms(self) -> list[str]:
        from django.conf import settings

        return settings.LAMB_LOG_JSON_HIDE

    hide_fields = lazy_descriptor(_hide_atoms, [])

    def to_json(self, record):
        # override parent to adapt non ascii
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

    def json_record(self, message, extra, record):
        result = super().json_record(message, extra, record)
        result["ts"] = self.formatTime(record, self.datefmt)
        result["pid"] = os.getpid()
        result["level"] = record.levelname
        result["moduleName"] = record.module
        result["fileName"] = record.filename
        result["lineNo"] = record.lineno

        for k in self.hide_fields:
            result.pop(k, None)

        # hide defaults
        result.pop("prefixno", None)

        return result


# # final formatters
# class LambFormatter(_TimeFormatMixin, logging.Formatter):
#     # utils
#     def _log_lines_format(self) -> str:
#         from django.conf import settings
#
#         return settings.LAMB_LOG_LINES_FORMAT
#
#     log_lines_format = lazy_descriptor(_log_lines_format, "DEFAULT")
#
#     def _format_message_prefix(self, record):
#         buffer = record.message.split("\n")
#         paths = []
#         for index, message_part in enumerate(buffer):
#             record.message = message_part
#             record.prefixno = index + 1
#             paths.append(self._style.format(record))
#         return "\n".join(paths)
#
#     def _format_message_single(self, record):
#         result = self._style.format(record)
#         return result.replace("\n", " ")
#
#     def _format_message_default(self, record):
#         return self._style.format(record)
#
#     def _collect_message(self, record: logging.LogRecord):
#         message = record.getMessage()
#         if record.exc_info:
#             # Cache the traceback text to avoid converting it multiple times
#             # (it's constant anyway)
#             if not record.exc_text:
#                 record.exc_text = self.formatException(record.exc_info)
#         if record.exc_text:
#             if message[-1:] != "\n":
#                 message = message + "\n"
#             message = message + record.exc_text
#         if record.stack_info:
#             if message[-1:] != "\n":
#                 message = message + "\n"
#             message = message + self.formatStack(record.stack_info)
#         return message
#
#     # contract
#     def format(self, record: logging.LogRecord) -> str:  # noqa: A003
#         if self.usesTime():
#             record.asctime = self.formatTime(record, self.datefmt)
#         record.message = self._collect_message(record)
#
#         match self.log_lines_format:
#             case "DEFAULT":
#                 return self._format_message_default(record)
#             case "PREFIX":
#                 return self._format_message_prefix(record)
#             case "SINGLE_LINE":
#                 return self._format_message_single(record)
#             case _:
#                 raise ValueError(f"Unknown log line format: {self.log_lines_format}")


class LambFormatter(_BaseFormatter):
    pass


class LambJSONFormatter(_LambJSONFormatterBase):

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
    def _format(self, record):  # noqa: A003
        from django.conf import settings
        from django.urls import resolve

        # Lamb Framework
        from lamb.utils import get_current_request

        # combine exception in same message
        message = record.getMessage()
        if record.exc_info is not None:
            message = f"{message}\n{self.formatException(record.exc_info)}"

        # main data
        data = {
            "ts": self.formatTime(record, self.datefmt),
            "pid": os.getpid(),
            "level": record.levelname,
            "msg": message,
            "moduleName": record.module,
            "fileName": record.filename,
            "lineNo": record.lineno,
        }

        # add status code
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
            data["statusCode"] = status_code

        # add context
        try:
            data["context"] = record.context
        except AttributeError:
            pass

        # add specific django info
        request = get_current_request()
        if request is not None:
            data["httpMethod"] = request.method
            data["httpUrl"] = request.path

            try:
                etm = request.lamb_execution_meter
                data["elapsedTimeMs"] = round((record.created - etm.start_time) * 1000, 3)
            except AttributeError:
                pass

            try:
                data["xray"] = request.xray
            except AttributeError:
                pass

            try:
                data["userId"] = request.app_user_id
            except Exception:
                pass

            try:
                data["trackId"] = request.lamb_track_id
            except AttributeError:
                pass

            try:
                resolved = resolve(request.path)
                data["urlName"] = resolved.url_name
            except Exception:
                pass

            for hide_key in settings.LAMB_LOG_JSON_HIDE:
                data.pop(hide_key, None)
        return self.to_json(data)
