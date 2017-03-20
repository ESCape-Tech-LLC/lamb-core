__author__ = 'KoNEW'
#-*- coding: utf-8 -*-

from datetime import datetime

from sqlalchemy import Column, text, ForeignKey
from sqlalchemy.dialects.mysql import BIGINT, VARCHAR, TIMESTAMP, FLOAT
from sqlalchemy.orm import relationship

from marble.db.session import DeclarativeBase
from marble.db.mixins import TableConfigMixin

class MarbleExecutionTimeMetric(DeclarativeBase, TableConfigMixin):
    __tablename__ = 'marble_execution_time_metric'

    # columns
    metric_id = Column(BIGINT(unsigned=True), nullable=False, primary_key=True, autoincrement=True)
    app_name = Column(VARCHAR(100))
    url_name = Column(VARCHAR(100))
    http_method = Column(VARCHAR(15))
    start_time = Column(TIMESTAMP(), nullable=False, default=datetime.now(), server_default=text('CURRENT_TIMESTAMP'))
    elapsed_time = Column(FLOAT(), nullable=False, default=0.0, server_default=text('0'))

    # relations
    markers = relationship('MarbleExecutionTimeMarker', cascade='all', backref='metric')
    def __init__(self):
        self.app_name = 'INVALID'
        self.url_name = 'INVALID'
        self.http_method = None
        self.start_time = datetime.now()
        self.elapsed_time = -1.0


class MarbleExecutionTimeMarker(DeclarativeBase, TableConfigMixin):
    __tablename__ = 'marble_execution_time_marker'

    #columns
    f_metric_id = Column(BIGINT(unsigned=True),
                         ForeignKey(MarbleExecutionTimeMetric.metric_id, onupdate='CASCADE', ondelete='CASCADE'),
                         nullable=False)
    marker_id = Column(BIGINT(unsigned=True), nullable=False, primary_key=True, autoincrement=True)
    absolute_interval = Column(FLOAT(), nullable=False)
    relative_interval = Column(FLOAT(), nullable=False)
    percentage = Column(FLOAT(), nullable=False)
    marker = Column(VARCHAR(100))
