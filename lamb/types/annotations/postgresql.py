from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Union

# SQLAlchemy
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
from typing_extensions import Annotated

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
int_s = Annotated[int, mapped_column(SMALLINT)]
int_b = Annotated[int, mapped_column(BIGINT)]
int_i = Annotated[int, mapped_column(INTEGER)]

bool_f = Annotated[bool, mapped_column(BOOLEAN, server_default=text("FALSE"))]
bool_t = Annotated[bool, mapped_column(BOOLEAN, server_default=text("TRUE"))]

uuid_pk = Annotated[uuid.UUID, mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())]

str_v = Annotated[str, mapped_column(VARCHAR)]
str_ci = Annotated[str, mapped_column(CITEXT)]
str_ts = Annotated[str, mapped_column(TSVECTOR)]

timestamp_tz = Annotated[datetime, mapped_column(TIMESTAMP(timezone=True))]

jsonb = Annotated[Union[List[Any], Dict[str, Any]], mapped_column(JSONB)]
