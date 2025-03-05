import logging

from functools import wraps


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
