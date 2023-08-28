from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional  # noqa: F401
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
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.engine import Connection

# Lamb Framework
from lamb.exc import ImproperlyConfiguredError
from lamb.types import JSONType, DeviceInfo, DeviceInfoType
from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin

__all__ = ["LambExecutionTimeMarker", "LambExecutionTimeMetric"]

logger = logging.getLogger(__name__)


# TODO: tsdb on markers


class LambExecutionTimeMetric(ResponseEncodableMixin, DeclarativeBase):
    __tablename__ = "lamb_execution_time_metric"

    # columns
    metric_id: Mapped[int] = Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    start_time: Mapped[datetime] = Column(
        TIMESTAMP(timezone=False),
        nullable=False,
        primary_key=True,
        default=datetime.now(),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    app_name: Mapped[Optional[str]] = Column(VARCHAR(100), nullable=True)
    url_name: Mapped[Optional[str]] = Column(VARCHAR(100), nullable=True)
    http_method: Mapped[Optional[str]] = Column(VARCHAR(15), nullable=True)
    headers: Mapped[Optional[Dict[str, Any]]] = Column(JSONType, nullable=True)
    args: Mapped[Optional[Dict[str, Any]]] = Column(JSONType, nullable=True)
    device_info: Mapped[Optional[DeviceInfo]] = Column(
        DeviceInfoType,
        nullable=True,
        default=None,
        server_default=text("NULL"),
    )
    status_code: Mapped[Optional[int]] = Column(SMALLINT, nullable=True)
    elapsed_time: Mapped[float] = Column(FLOAT, nullable=False, default=0.0, server_default=text("0"))
    context: Mapped[Optional[Any]] = Column(JSONType, nullable=True)

    # relations
    markers = relationship(
        "LambExecutionTimeMarker",
        back_populates="metric",
        primaryjoin="LambExecutionTimeMetric.metric_id == foreign(LambExecutionTimeMarker.metric_id)",
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
    if settings.LAMB_EXECUTION_TIME_TIMESCALE_COMPRESS_AFTER:
        statement += (
            f"ALTER TABLE {target.fullname} SET (timescaledb.compress); "
            f"SELECT add_compression_policy('{target.fullname}', "
            f"INTERVAL '{settings.LAMB_EXECUTION_TIME_TIMESCALE_COMPRESS_AFTER}');"
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
    metric_id: Mapped[int] = Column(BIGINT, nullable=False)
    marker_id: Mapped[int] = Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    absolute_interval: Mapped[float] = Column(FLOAT, nullable=False)
    relative_interval: Mapped[float] = Column(FLOAT, nullable=False)
    percentage: Mapped[float] = Column(FLOAT, nullable=False)
    marker: Mapped[Optional[str]] = Column(VARCHAR, nullable=True)

    # relations
    metric = relationship(
        LambExecutionTimeMetric,
        uselist=False,
        back_populates="markers",
        primaryjoin="foreign(LambExecutionTimeMarker.metric_id) == LambExecutionTimeMetric.metric_id",
    )  # type: LambExecutionTimeMetric

    # meta
    __table_args__ = (Index("lamb_execution_time_marker_metric_id_idx", metric_id),)
