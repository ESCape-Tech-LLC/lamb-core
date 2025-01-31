from __future__ import annotations

import os
import logging
from typing import Any, Dict

__all__ = ["inject_logging_factory", "get_gunicorn_logging_dict"]

# Lamb Framework
from lamb.log.constants import LAMB_LOG_FORMAT_GUNICORN_SIMPLE


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
    is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
    if is_gunicorn:
        _logger = logging.getLogger("gunicorn.error")
    else:
        _logger = logging.getLogger("django")

    _logger.info("Lamb logging factory injected")


def get_gunicorn_logging_dict(log_formatter_cls: str, fmt: str = LAMB_LOG_FORMAT_GUNICORN_SIMPLE) -> Dict[str, Any]:
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
