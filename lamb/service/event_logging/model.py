from __future__ import annotations

import enum
from typing import List
from datetime import datetime

# SQLAlchemy
from sqlalchemy import BOOLEAN, VARCHAR, TIMESTAMP, Column, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import ENUM, INET, JSONB

# Lamb Framework
from lamb.types import DeviceInfoType
from lamb.db.mixins import TimeMarksMixin
from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin

__all__ = ["EventSourceType", "EventTrack", "EventRecord"]


@enum.unique
class EventSourceType(str, enum.Enum):
    SERVER = "SERVER"
    CLIENT = "CLIENT"


class EventTrack(ResponseEncodableMixin, TimeMarksMixin, DeclarativeBase):
    __abstract__ = True

    __tablename__ = "lamb_event_track"

    # columns
    track_id = Column(
        UUIDType(binary=True, native=True), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    device_info = Column(DeviceInfoType, nullable=True, default=None, server_default=text("NULL"))

    # relations
    @declared_attr
    def records(self) -> List["EventRecord"]:
        return relationship(
            "EventRecord", uselist=True, passive_updates=True, passive_deletes=True
        )  # type: List[EventRecord]


class EventRecord(ResponseEncodableMixin, TimeMarksMixin, DeclarativeBase):
    __abstract__ = True

    __tablename__ = "lamb_event_record"

    __event_track_model__ = EventTrack

    # columns
    record_id = Column(
        UUIDType(binary=True, native=True), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    event = Column(VARCHAR, nullable=True, default=None, server_default=text("NULL"))
    timemark = Column(TIMESTAMP, nullable=False, default=datetime.now, server_default=text("CURRENT_TIMESTAMP"))
    timemark_ntp = Column(BOOLEAN, nullable=False, default=False, server_default=text("FALSE"))
    context = Column(JSONB, nullable=True, default={}, server_default=text("'{}'"))
    ip_address = Column(INET, nullable=True, default=None, server_default=text("NULL"))

    @declared_attr
    def source(self):
        return Column(
            ENUM(EventSourceType, name="event_source", schema=self.metadata.schema),
            nullable=False,
            default=EventSourceType.CLIENT,
            server_default=EventSourceType.CLIENT.value,
        )

    @declared_attr
    def track_id(self):
        return Column(
            UUIDType(binary=True, native=True),
            ForeignKey(f"{self.__event_track_model__.__tablename__}.track_id", onupdate="CASCADE", ondelete="CASCADE"),
            nullable=False,
        )

    # relations
    @declared_attr
    def track(self):
        return relationship(self.__event_track_model__.__name__, uselist=False)  # type: EventTrack
