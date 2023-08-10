from __future__ import annotations

import logging
from typing import List  # noqa: F401
from datetime import datetime

from django.conf import settings

# SQLAlchemy
from sqlalchemy import (
    FLOAT,
    BIGINT,
    VARCHAR,
    SMALLINT,
    TIMESTAMP,
    Index,
    Table,
    Column,
    text,
    event,
)
from sqlalchemy.orm import relationship
from sqlalchemy.engine import Connection
from sqlalchemy.dialects.postgresql import JSONB

# Lamb Framework
from lamb.exc import ImproperlyConfiguredError
from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin

__all__ = ["LambExecutionTimeMarker", "LambExecutionTimeMetric"]

# Lamb Framework
from lamb.types import DeviceInfoType

logger = logging.getLogger(__name__)


class LambExecutionTimeMetric(ResponseEncodableMixin, DeclarativeBase):
    __tablename__ = "lamb_execution_time_metric"

    # columns
    metric_id = Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    start_time = Column(
        TIMESTAMP(), nullable=False, primary_key=True, default=datetime.now(), server_default=text("CURRENT_TIMESTAMP")
    )
    app_name = Column(VARCHAR(100))
    url_name = Column(VARCHAR(100))
    http_method = Column(VARCHAR(15))
    # TODO: Migrate headers, args, and context to custom JSONB type
    headers = Column(JSONB)
    args = Column(JSONB)
    device_info = Column(DeviceInfoType, nullable=True, default=None, server_default=text("NULL"))
    status_code = Column(SMALLINT)
    elapsed_time = Column(FLOAT(), nullable=False, default=0.0, server_default=text("0"))
    context = Column(JSONB)

    # relations
    markers = relationship(
        "LambExecutionTimeMarker",
        back_populates="metric",
        primaryjoin="LambExecutionTimeMetric.metric_id == foreign(LambExecutionTimeMarker.f_metric_id)",
    )  # type: List[LambExecutionTimeMarker]

    # methods
    def __init__(self):
        self.app_name = "INVALID"
        self.url_name = "INVALID"
        self.http_method = None
        self.headers = None
        self.args = None
        self.status_code = None
        self.start_time = datetime.now()
        self.elapsed_time = -1.0

    # meta
    __table_args__ = (Index("lamb_execution_time_metric_start_time_idx", start_time.desc()),)


@event.listens_for(LambExecutionTimeMetric.__table__, "after_create")
def execution_time_create_hypertable(target: Table, connection: Connection, **kwargs):
    if not settings.LAMB_EXECUTION_TIME_TIMESCALE:
        return
    statement = f"""
        SELECT create_hypertable(
            '{target.fullname}',
            'start_time',
            chunk_time_interval => INTERVAL '{settings.LAMB_EXECUTION_TIME_TIMESCALE_CHUNK_INTERVAL}'
        );
    """
    if settings.LAMB_EXECUTION_TIME_TIMESCALE_RETENTION_INTERVAL:
        statement += (
            f"SELECT add_retention_policy('{target.fullname}', "
            f"INTERVAL '{settings.LAMB_EXECUTION_TIME_TIMESCALE_RETENTION_INTERVAL}');"
        )
    try:
        connection.execute(statement)
    except Exception as e:
        raise ImproperlyConfiguredError(
            "Unable to convert execution time metric table to hypertable. "
            "Make sure that timescaledb extension is installed"
        ) from e


class LambExecutionTimeMarker(ResponseEncodableMixin, DeclarativeBase):
    __tablename__ = "lamb_execution_time_marker"
    # columns
    f_metric_id = Column(BIGINT, nullable=False, index=True)
    marker_id = Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    absolute_interval = Column(FLOAT(), nullable=False)
    relative_interval = Column(FLOAT(), nullable=False)
    percentage = Column(FLOAT(), nullable=False)
    marker = Column(VARCHAR)

    # relations
    metric = relationship(
        LambExecutionTimeMetric,
        uselist=False,
        back_populates="markers",
        primaryjoin="foreign(LambExecutionTimeMarker.f_metric_id) == LambExecutionTimeMetric.metric_id",
    )  # type: LambExecutionTimeMetric

    # meta
    __table_args__ = (Index("lamb_execution_time_metric_f_metric_id_idx", f_metric_id),)
