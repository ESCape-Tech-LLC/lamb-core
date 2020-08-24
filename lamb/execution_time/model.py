#-*- coding: utf-8 -*-
__author__ = 'KoNEW'


from datetime import datetime
from typing import List

from sqlalchemy import Column, text, ForeignKey, Index
from sqlalchemy import BIGINT, VARCHAR, TIMESTAMP, FLOAT
from sqlalchemy.orm import relationship

from lamb.db.session import DeclarativeBase
from lamb.db.mixins import TableConfigMixin
from lamb.json.mixins import ResponseEncodableMixin


__all__ = ['LambExecutionTimeMarker', 'LambExecutionTimeMetric']


class LambExecutionTimeMetric(ResponseEncodableMixin, DeclarativeBase):
    __tablename__ = 'lamb_execution_time_metric'

    # columns
    metric_id = Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    app_name = Column(VARCHAR(100))
    url_name = Column(VARCHAR(100))
    http_method = Column(VARCHAR(15))
    start_time = Column(TIMESTAMP(), nullable=False, default=datetime.now(), server_default=text('CURRENT_TIMESTAMP'))
    elapsed_time = Column(FLOAT(), nullable=False, default=0.0, server_default=text('0'))

    # relations
    markers = relationship('LambExecutionTimeMarker', cascade='all')  # type: List[LambExecutionTimeMarker]

    # methods
    def __init__(self):
        self.app_name = 'INVALID'
        self.url_name = 'INVALID'
        self.http_method = None
        self.start_time = datetime.now()
        self.elapsed_time = -1.0

    # meta
    __table_args__ = (
        Index('lamb_execution_time_metric_start_time_idx', start_time.desc()),
    )


class LambExecutionTimeMarker(ResponseEncodableMixin, DeclarativeBase):
    __tablename__ = 'lamb_execution_time_marker'
    #columns
    f_metric_id = Column(BIGINT,
                         ForeignKey(LambExecutionTimeMetric.metric_id, onupdate='CASCADE', ondelete='CASCADE'),
                         nullable=False, index=True)
    marker_id = Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    absolute_interval = Column(FLOAT(), nullable=False)
    relative_interval = Column(FLOAT(), nullable=False)
    percentage = Column(FLOAT(), nullable=False)
    marker = Column(VARCHAR(100))

    # relations
    metric = relationship(LambExecutionTimeMetric, uselist=False)  # type: LambExecutionTimeMetric

    # meta
    __table_args__ = (
        Index('lamb_execution_time_metric_f_metric_id_idx', f_metric_id),
    )
