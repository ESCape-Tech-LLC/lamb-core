# -*- coding: utf-8 -*-

import enum
from datetime import datetime
from typing import List

from sqlalchemy import Column, ForeignKey, BOOLEAN, TIMESTAMP, VARCHAR, text
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, validates
from sqlalchemy_utils import UUIDType

from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin
from lamb.types import DeviceInfoType
from lamb.types.intenum import IntEnumType
from lamb.types.jsonb import SUAJSONBType


__all__ = ['EventSourceType', 'EventTrack', 'EventRecord']


IP_MAX_LENGTH = 20


class EventSourceType(enum.IntEnum):
    SERVER = 0
    CLIENT = 1


class EventTrack(ResponseEncodableMixin, DeclarativeBase):
    __abstract__ = True

    __tablename__ = 'lamb_event_track'

    # columns
    track_id = Column(UUIDType(binary=True, native=True), nullable=False, primary_key=True,
                      server_default=text('gen_random_uuid()'))
    source = Column(
        IntEnumType(EventSourceType),
        nullable=False,
        default=EventSourceType.SERVER,
        server_default=str(EventSourceType.SERVER.value)
    )
    device_info = Column(DeviceInfoType, nullable=True, default=None, server_default=text('NULL'))
    ip_address = Column(VARCHAR(IP_MAX_LENGTH), nullable=True, default=None, server_default=text('NULL'))


class EventRecord(ResponseEncodableMixin, DeclarativeBase):
    __abstract__ = True

    __tablename__ = 'lamb_event_record'

    __event_track_model__ = EventTrack

    # columns
    record_id = Column(UUIDType(binary=True, native=True), nullable=False, primary_key=True,
                       server_default=text('gen_random_uuid()'))

    @declared_attr
    def track_id(self):
        return Column(
            UUIDType(binary=True, native=True),
            ForeignKey(f'{self.__event_track_model__.__tablename__}.track_id', onupdate='CASCADE', ondelete='CASCADE'),
            nullable=False
        )

    timemark = Column(TIMESTAMP, nullable=False, default=datetime.now, server_default=text('CURRENT_TIMESTAMP'))
    timemark_ntp = Column(BOOLEAN, nullable=False, default=False, server_default=text('FALSE'))
    context = Column(SUAJSONBType(native=True), nullable=True)

    # relations
    @declared_attr
    def track(self):
        return relationship(self.__event_track_model__.__name__, uselist=False, backref='records')  # type: EventTrack

    @validates('ip_address')
    def validate_variable_name(self, key, value):
        if not isinstance(value, str):
            return value

        return value[:IP_MAX_LENGTH]
