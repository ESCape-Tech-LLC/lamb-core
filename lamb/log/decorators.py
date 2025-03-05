import logging

from functools import wraps


class LoggerFilter(logging.Filter):
    def __init__(self, endpoint, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint = endpoint

    def filter(self, record: logging.LogRecord) -> bool:
        result = record.getMessage().find(self.endpoint) == -1
        return result


def suppress_logging(logger_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name)
            # Store original handlers
            original_handler = logger.handlers.copy()
            # Removing handlers
            for handler in original_handler:
                logger.removeHandler(handler)
            try:
                result = func(*args, **kwargs)
            finally:
                for handler in original_handler:
                    logger.addHandler(handler)
            return result
        return wrapper
    return decorator


def suppress_gunicorn_endpoint_logging(gunicorn_logger_name, endpoint_path):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(gunicorn_logger_name)
            logger.addFilter(LoggerFilter(endpoint=endpoint_path))
            return func(*args, **kwargs)
        return wrapper
    return decorator
