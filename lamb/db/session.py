# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


from django.conf import settings

import sqlalchemy as sa
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from furl import furl

from lamb.exc import ServerError

__all__ = [
    'DeclarativeBase', 'metadata', 'lamb_db_session_maker', 'declarative_base', '_engine'
]

logger = logging.getLogger(__name__)


try:
    # basic
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

    # pre-fill default engine opts and modify with server settings
    ENGINE_OPTS_POOLED = settings.DATABASES['default'].get('ENGINE_OPTS_POOLED', None)
    if _ENGINE == 'postgresql' and ENGINE_OPTS_POOLED is None:
        ENGINE_OPTS_POOLED = {
            'pool_recycle': 3600,
            'executemany_mode': 'values',
            'executemany_values_page_size': 10000,
            'executemany_batch_page_size': 500
        }
    if ENGINE_OPTS_POOLED is None:
        ENGINE_OPTS_POOLED = {}
    logger.info(f'database engine options would be used for pooled connections: {ENGINE_OPTS_POOLED}')
    _engine = create_engine(CONNECTION_STRING, **ENGINE_OPTS_POOLED)

    ENGINE_OPTS_NON_POOLED = settings.DATABASES['default'].get('ENGINE_OPTS_NON_POOLED', None)
    if _ENGINE == 'postgresql' and ENGINE_OPTS_NON_POOLED is None:
        ENGINE_OPTS_NON_POOLED = {
            'executemany_mode': 'values',
            'executemany_values_page_size': 10000,
            'executemany_batch_page_size': 500
        }
    if ENGINE_OPTS_NON_POOLED is None:
        ENGINE_OPTS_NON_POOLED = {}
    logger.info(f'database engine options would be used for non-pooled connections: {ENGINE_OPTS_NON_POOLED}')
    _no_pool_engine = create_engine(CONNECTION_STRING, poolclass=NullPool, **ENGINE_OPTS_NON_POOLED)
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
