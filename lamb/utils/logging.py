import logging
from logging import Formatter, LogRecord

from django.conf import settings

__all__ = ["LambFormatter", "inject_logging_factory"]


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


class LambFormatter(Formatter):
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
