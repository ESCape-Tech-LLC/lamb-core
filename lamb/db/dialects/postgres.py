import logging

from sqlalchemy.dialects.postgresql import ENUM

from lamb.contrib.handbook import HandbookEnumMixin
from lamb.exc import ImproperlyConfiguredError

logger = logging.getLogger(__name__)

__all__ = ["PGEnumMixin", "PG_ENUM"]


class PGEnumMixin(HandbookEnumMixin):
    __pg_name__ = None

    def __new__(cls, *args, **kwargs):
        if cls.__pg_name__ is None:
            logger.critical(f"__pg_name__ meta required on: {cls}")
            raise ImproperlyConfiguredError
        return super().__new__(cls, *args, **kwargs)


class PG_ENUM(ENUM):  # noqa: N801
    def __init__(self, *args, **kwargs):
        if len(args) == 1 and issubclass(args[0], PGEnumMixin):
            _enum = args[0]
            kwargs["values_callable"] = lambda obj: [e.value for e in obj]
            kwargs["name"] = _enum.__pg_name__
        super().__init__(*args, **kwargs)
