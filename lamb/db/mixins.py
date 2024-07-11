import re
from datetime import datetime

# SQLAlchemy
from sqlalchemy import TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declared_attr

__all__ = ["TableConfigMixin", "TimeMarksMixin", "TimeMarksMixinTZ"]


class TableConfigMixin(object):
    @declared_attr
    def __tablename__(cls):
        class_name = cls.__name__
        result = re.sub("(?<!^)(?=[A-Z])", "_", class_name).lower()
        return result

    __table_args__ = {"mysql_engine": "InnoDB"}


class TimeMarksMixin:
    # columns
    time_created: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        server_default=func.CURRENT_TIMESTAMP(),
        sort_order=-1,
    )
    time_updated: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        server_default=func.CURRENT_TIMESTAMP(),
        onupdate=func.CURRENT_TIMESTAMP(),
        sort_order=-1,
    )


class TimeMarksMixinTZ:
    # columns
    time_created: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.CURRENT_TIMESTAMP(),
        sort_order=-1,
    )
    time_updated: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.CURRENT_TIMESTAMP(),
        onupdate=func.CURRENT_TIMESTAMP(),
        sort_order=-1,
    )
