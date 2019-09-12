# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


from django.conf import settings

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from lamb.exc import ServerError

__all__ = [
    'DeclarativeBase', 'metadata', 'lamb_db_session_maker', '_engine', 'declarative_base'
]


try:
    _USER = settings.DATABASES['default'].get('USER', None)
    _NAME = settings.DATABASES['default'].get('NAME', None)
    _PASS = settings.DATABASES['default'].get('PASSWORD', None)
    _HOST = settings.DATABASES['default'].get('HOST', None)
    _ENGINE = settings.DATABASES['default'].get('ENGINE', None)
    _OPTS = settings.DATABASES['default'].get('CONNECT_OPTS', None)
    if _ENGINE is not None:
        _ENGINE = _ENGINE[_ENGINE.rindex('.')+1:]
    _CONNECTION_STRING = '%s://%s:%s@%s/%s?%s' % (_ENGINE, _USER, _PASS, _HOST, _NAME, _OPTS)
    _engine = create_engine(
        _CONNECTION_STRING,
        pool_recycle=3600
    )
except KeyError as e:
    raise ServerError('Database session constructor failed to get database params')


DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata
metadata.bind = _engine
_session_maker = sessionmaker(bind=_engine)


def lamb_db_session_maker() -> sa.orm.session.Session:
    """ Constructor for database sqlalchemy sessions """
    session = _session_maker()
    return session
