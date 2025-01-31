from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional  # noqa: F401

from sqlalchemy import (
    BIGINT,
    FLOAT,
    JSON,
    SMALLINT,
    TIMESTAMP,
    VARCHAR,
    Identity,
    Index,
    Table,
    event,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, mapped_column, relationship

from django.conf import settings

from lamb.db.session import DeclarativeBase
from lamb.exc import ImproperlyConfiguredError
from lamb.json.mixins import ResponseEncodableMixin

# from lamb.types import DeviceInfo, DeviceInfoType
from lamb.types.device_info_type import DeviceInfo, DeviceInfoType
from lamb.utils import tz_now

__all__ = ["LambExecutionTimeMarker", "LambExecutionTimeMetric"]

logger = logging.getLogger(__name__)


_JSON = JSON().with_variant(JSONB, "postgresql")


class LambExecutionTimeMetric(ResponseEncodableMixin, DeclarativeBase):
    __tablename__ = "lamb_execution_time_metric"

    # columns
    metric_id: Mapped[int] = mapped_column(BIGINT, Identity(always=True), primary_key=True, autoincrement=True)
    start_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        primary_key=True,
        server_default=func.CURRENT_TIMESTAMP(),
    )
    app_name: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    url_name: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    http_method: Mapped[Optional[str]] = mapped_column(VARCHAR(15))
    headers: Mapped[Optional[Dict[str, Any]]] = mapped_column(_JSON)
    args: Mapped[Optional[Dict[str, Any]]] = mapped_column(_JSON)
    device_info: Mapped[DeviceInfo] = mapped_column(
        DeviceInfoType,
        default=DeviceInfo(),
        server_default=text("'{}'::JSONB"),
    )
    status_code: Mapped[Optional[int]] = mapped_column(SMALLINT)
    elapsed_time: Mapped[float] = mapped_column(FLOAT, default=0.0, server_default=text("0"))
    context: Mapped[Optional[Any]] = mapped_column(_JSON, nullable=True)

    # relations
    markers: Mapped[List[LambExecutionTimeMarker]] = relationship(
        "LambExecutionTimeMarker",
        back_populates="metric",
        primaryjoin="LambExecutionTimeMetric.metric_id == foreign(LambExecutionTimeMarker.metric_id)",
    )

    # methods
    def __init__(self):
        self.app_name = "INVALID"
        self.url_name = "INVALID"
        self.http_method = None
        self.headers = None
        self.args = None
        self.status_code = None
        self.start_time = tz_now()
        self.elapsed_time = -1.0

    # meta
    __table_args__ = (Index("lamb_execution_time_metric_start_time_idx", start_time.desc()),)


@event.listens_for(LambExecutionTimeMetric.__table__, "after_create")
def execution_time_create_hypertable(target: Table, connection: Connection, **kwargs):
    if not settings.LAMB_EXECUTION_TIME_TIMESCALE:
        return
    statement = (
        f"SELECT create_hypertable('{target.fullname}','start_time',chunk_time_interval "
        f"=> INTERVAL '{settings.LAMB_EXECUTION_TIME_TIMESCALE_CHUNK_INTERVAL}');"
    )
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
        connection.execute(text(statement))
    except Exception as e:
        raise ImproperlyConfiguredError(
            "Unable to convert execution time metric table to hypertable. "
            "Make sure that timescaledb extension is installed"
        ) from e


class LambExecutionTimeMarker(ResponseEncodableMixin, DeclarativeBase):
    __tablename__ = "lamb_execution_time_marker"
    # columns
    metric_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    marker_id: Mapped[int] = mapped_column(
        BIGINT,
        Identity(always=True),
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    absolute_interval: Mapped[float] = mapped_column(FLOAT, nullable=False)
    relative_interval: Mapped[float] = mapped_column(FLOAT, nullable=False)
    percentage: Mapped[float] = mapped_column(FLOAT, nullable=False)
    marker: Mapped[Optional[str]] = mapped_column(VARCHAR, nullable=True)

    # relations
    metric = relationship(
        LambExecutionTimeMetric,
        uselist=False,
        back_populates="markers",
        primaryjoin="foreign(LambExecutionTimeMarker.metric_id) == LambExecutionTimeMetric.metric_id",
    )  # type: LambExecutionTimeMetric

    # meta
    __table_args__ = (Index("lamb_execution_time_marker_metric_id_idx", metric_id),)
