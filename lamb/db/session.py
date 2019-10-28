# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


from django.conf import settings

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from furl import furl

from lamb.exc import ServerError

__all__ = [
    'DeclarativeBase', 'metadata', 'lamb_db_session_maker', 'declarative_base', '_engine'
]


try:
    _USER = settings.DATABASES['default'].get('USER', None)
    _NAME = settings.DATABASES['default'].get('NAME', None)
    _PASS = settings.DATABASES['default'].get('PASSWORD', None)
    _HOST = settings.DATABASES['default'].get('HOST', None)
    _ENGINE = settings.DATABASES['default'].get('ENGINE', None)
    _OPTS = settings.DATABASES['default'].get('CONNECT_OPTS', None)
    if _ENGINE is not None:
        _ENGINE = _ENGINE[_ENGINE.rindex('.') + 1:]

    if _ENGINE == 'sqlite3':
        # monkey patch on django/sqlalchemy difference
        _ENGINE = 'sqlite'

    CONNECTION_STRING = furl()
    CONNECTION_STRING.scheme = _ENGINE
    CONNECTION_STRING.username = _USER
    CONNECTION_STRING.password = _PASS
    if _HOST is not None:
        CONNECTION_STRING.host = _HOST
    else:
        CONNECTION_STRING.host = ''
    if _NAME is not None:
        CONNECTION_STRING.path.add(_NAME)
    if _OPTS is not None:
        CONNECTION_STRING.args.update(_OPTS)
    CONNECTION_STRING = CONNECTION_STRING.url

    _engine = create_engine(CONNECTION_STRING, pool_recycle=3600)
    _no_pool_engine = create_engine(CONNECTION_STRING, poolclass=NullPool)
    print(f'connection string: {CONNECTION_STRING}')
except KeyError as e:
    raise ServerError('Database session constructor failed to get database params')


DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata
metadata.bind = _engine
_session_maker = sessionmaker(bind=_engine)
_no_poll_session_maker = sessionmaker(bind=_no_pool_engine)


def lamb_db_session_maker(pooled: bool = True) -> sa.orm.session.Session:
    """ Constructor for database sqlalchemy sessions """
    if pooled:
        session = _session_maker()
    else:
        session = _no_poll_session_maker()
    return session
