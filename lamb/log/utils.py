import os
import logging

__all__ = ["inject_logging_factory"]


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
