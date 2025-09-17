from __future__ import annotations

import logging
import os
from typing import Any

__all__ = ["inject_logging_factory", "get_gunicorn_logging_dict"]


from lamb.log.constants import LAMB_LOG_FORMAT_GUNICORN_SIMPLE


def inject_logging_factory():
    old_factory = logging.getLogRecordFactory()

    def _logging_factory(*args, **kwargs):
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
        record.prefixno = 1

        # return
        return record

    logging.setLogRecordFactory(_logging_factory)
    is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
    _logger = logging.getLogger("gunicorn.error") if is_gunicorn else logging.getLogger("django")

    _logger.info("Lamb logging factory injected")


def get_gunicorn_logging_dict(log_formatter_cls: str, fmt: str = LAMB_LOG_FORMAT_GUNICORN_SIMPLE) -> dict[str, Any]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "root": {
            "level": "INFO",
            "handlers": [],
        },
        "loggers": {
            "gunicorn.error": {
                "level": "INFO",
                "handlers": ["error_console"],
                "propagate": True,
                "qualname": "gunicorn.error",
            },
            "gunicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": True,
                "qualname": "gunicorn.access",
            },
        },
        "formatters": {
            "generic": {
                "class": log_formatter_cls,
                "format": fmt,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "generic",
                "stream": "ext://sys.stdout",
            },
            "error_console": {
                "class": "logging.StreamHandler",
                "formatter": "generic",
                "stream": "ext://sys.stderr",
            },
        },
    }
