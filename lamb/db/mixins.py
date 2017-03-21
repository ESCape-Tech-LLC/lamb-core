__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

import re
from datetime import datetime
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import Column, text, TIMESTAMP


class TableConfigMixin(object):

    @declared_attr
    def __tablename__(cls):
        class_name = cls.__name__
        result = re.sub('(?<!^)(?=[A-Z])', '_', class_name).lower()
        return result

    __table_args__ = (
        {
            'mysql_engine': 'InnoDB'
        }
    )


class TimeMarksMixin(object):
    # columns
    time_created = Column(TIMESTAMP, nullable=False, default=datetime.now, server_default=text('CURRENT_TIMESTAMP'))
    time_updated = Column(TIMESTAMP, nullable=False, default=datetime.now, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), onupdate=datetime.now)