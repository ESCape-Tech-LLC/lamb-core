from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import (
    BIGINT,
    BOOLEAN,
    CITEXT,
    INTEGER,
    JSONB,
    SMALLINT,
    TIMESTAMP,
    TSVECTOR,
    UUID,
    VARCHAR,
)
from sqlalchemy.orm import mapped_column

__all__ = [
    "uuid_pk",
    "str_v",
    "str_ci",
    "str_ts",
    "int_s",
    "int_i",
    "int_b",
    "bool_f",
    "bool_t",
    "timestamp_tz",
    "jsonb",
]

# annotations
int_s: type[int] = Annotated[int, mapped_column(SMALLINT)]
int_b: type[int] = Annotated[int, mapped_column(BIGINT)]
int_i: type[int] = Annotated[int, mapped_column(INTEGER)]

bool_f: type[bool] = Annotated[bool, mapped_column(BOOLEAN, server_default=text("FALSE"))]
bool_t: type[bool] = Annotated[bool, mapped_column(BOOLEAN, server_default=text("TRUE"))]

uuid_pk: type[UUID] = Annotated[
    uuid.UUID, mapped_column(UUID, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
]

str_v: type[str] = Annotated[str, mapped_column(VARCHAR)]
str_ci: type[str] = Annotated[str, mapped_column(CITEXT)]
str_ts: type[str] = Annotated[str, mapped_column(TSVECTOR)]

timestamp_tz: type[datetime] = Annotated[datetime, mapped_column(TIMESTAMP(timezone=True))]

jsonb: type[dict] = Annotated[list[Any] | dict[str, Any], mapped_column(JSONB)]
