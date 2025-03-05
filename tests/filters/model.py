from sqlalchemy import Column, Integer, DateTime, SMALLINT

from lamb.db import DeclarativeBase


class Actor(DeclarativeBase):
    __tablename__ = "actor"

    actor_id = Column(SMALLINT, primary_key=True)

class DatetimeModel(DeclarativeBase):
    __tablename__ = "test_datetime"

    __table_args__ = {"comment": "Table used to check filter for datetime"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_datetime_tz = Column(DateTime(timezone=True), nullable=False)
    record_datetime = Column(DateTime(timezone=False), nullable=False)
