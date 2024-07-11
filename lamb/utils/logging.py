import logging
import datetime
from logging import Formatter, LogRecord

try:
    from gunicorn.glogging import SafeAtoms
except ImportError:
    SafeAtoms = object()

from django.conf import settings
from django.urls import resolve

from lazy import lazy
from json_log_formatter import JSONFormatter, _json_serializable

__all__ = ["LambFormatter", "LambJSONFormatter", "inject_logging_factory"]


logger = logging.getLogger(__name__)


def inject_logging_factory():
    old_factory = logging.getLogRecordFactory()

    def _logging_factory(*args, **kwargs):
        # Lamb Framework
        from lamb.utils import get_current_request

        record = old_factory(*args, **kwargs)

        # attach request attributes
        r = get_current_request()
        _fields = ["app_user_id", "xray"]

        for field in _fields:
            try:
                setattr(record, field, getattr(r, field))
            except Exception:
                setattr(record, field, None)

        # attach log prefix number attribute default
        setattr(record, "prefixno", 1)

        # return
        return record

    logging.setLogRecordFactory(_logging_factory)
    logger.warning("Lamb logging factory injected")


class TimeFormatMixin:
    @lazy
    def format_time_sep(self) -> str:
        from django.conf import settings

        return settings.LAMB_LOG_FORMAT_TIME_SEP

    @lazy
    def format_time_spec(self) -> str:
        from django.conf import settings

        return settings.LAMB_LOG_FORMAT_TIME_SPEC

    def formatTime(self, record: LogRecord, datefmt: str | None = ...) -> str:
        dt = datetime.datetime.fromtimestamp(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat(sep=self.format_time_sep, timespec=self.format_time_spec)


class LambFormatter(TimeFormatMixin, Formatter):
    def __init__(self, *args, **kwargs):
        super(LambFormatter, self).__init__(*args, **kwargs)
        try:
            log_lines_format = settings.LAMB_LOG_LINES_FORMAT
        except AttributeError:
            log_lines_format = "DEFAULT"

        if log_lines_format in "PREFIX":
            self.formatMessage = self._prefix_formatting
        elif log_lines_format == "SINGLE_LINE":
            self.formatMessage = self._single_line_formatting
        else:
            self.formatMessage = self._default_formatting

    def _prefix_formatting(self, record):
        buffer = record.message.split("\n")
        paths = []
        for index, message_part in enumerate(buffer):
            record.message = message_part
            record.prefixno = index + 1
            paths.append(self._style.format(record))
        return "\n".join(paths)

    def _single_line_formatting(self, record):
        result = self._style.format(record)
        return result.replace("\n", " ")

    def _default_formatting(self, record):
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

    def format(self, record: LogRecord) -> str:  # noqa: A003
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        record.message = self._collect_message(record)
        return self.formatMessage(record)


class LambJSONFormatter(TimeFormatMixin, JSONFormatter):
    def format(self, record):  # noqa: A003
        from django.conf import settings

        # Lamb Framework
        from lamb.utils import get_current_request

        message = record.getMessage()
        if record.exc_info is not None:
            message = f"{message}\n{self.formatException(record.exc_info)}"

        data = {
            "level": record.levelname,
            "ts": self.formatTime(record, self.datefmt) if self.usesTime() else None,
            "msg": message,
            "moduleName": record.module,
            "fileName": record.filename,
            "lineNo": record.lineno,
        }
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
        try:
            data["context"] = record.context
        except AttributeError:
            pass
        request = get_current_request()
        if request is not None:
            # TODO responseBody ???
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
                data["userId"] = request.er_user.user_id
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

    def to_json(self, record):
        # adapt to ascii
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
