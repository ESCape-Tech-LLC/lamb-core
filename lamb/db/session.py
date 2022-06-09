# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


from django.conf import settings

import sqlalchemy as sa
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from furl import furl

from lamb.exc import ServerError

__all__ = [
    'DeclarativeBase', 'metadata', 'lamb_db_session_maker', 'declarative_base', '_engine',
    'async_session_factory', 'async_session_factory_noloop', 'create_engine', 'create_async_engine'
]

logger = logging.getLogger(__name__)


try:
    # TODO: add support for project connection definition with callbacks
    # basic
    _USER = settings.DATABASES['default'].get('USER', None)
    _NAME = settings.DATABASES['default'].get('NAME', None)
    _PASS = settings.DATABASES['default'].get('PASSWORD', None)
    _HOST = settings.DATABASES['default'].get('HOST', None)
    _ENGINE = settings.DATABASES['default'].get('ENGINE', None)
    _OPTS = settings.DATABASES['default'].get('CONNECT_OPTS', None)
    _PORT = settings.DATABASES['default'].get('PORT', None)
    _SESSION_OPTS = settings.DATABASES['default'].get('SESSION_OPTS', {})
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
    if _PORT is not None:
        CONNECTION_STRING.port = int(_PORT)
    if _OPTS is not None:
        CONNECTION_STRING.args.update(_OPTS)
    CONNECTION_STRING = CONNECTION_STRING.url
    logger.info(f'CONNECTION_STRING{CONNECTION_STRING}')

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
    # logger.info(f'database engine options would be used for pooled connections: {ENGINE_OPTS_POOLED},'
    #             f' session_opts: {_SESSION_OPTS}')
    logger.info(f'database.  SYNC options[pooled =  True]: engine_opts={ENGINE_OPTS_POOLED}'
                f', session_opts={_SESSION_OPTS}')

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
    logger.info(f'database.  SYNC options[pooled = False]: engine_opts={ENGINE_OPTS_NON_POOLED}'
                f', session_opts={_SESSION_OPTS}')
    # logger.info(f'database engine options would be used for non-pooled connections: {ENGINE_OPTS_NON_POOLED},'
    #             f' session_opts: {_SESSION_OPTS}')
    _no_pool_engine = create_engine(CONNECTION_STRING, poolclass=NullPool, **ENGINE_OPTS_NON_POOLED)
except KeyError as e:
    raise ServerError('Database session constructor failed to get database params')


DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata
metadata.bind = _engine
_session_maker = sessionmaker(bind=_engine, **_SESSION_OPTS)
_no_poll_session_maker = sessionmaker(bind=_no_pool_engine, **_SESSION_OPTS)


def lamb_db_session_maker(pooled: bool = True) -> sa.orm.session.Session:
    """ Constructor for database sqlalchemy sessions """
    if pooled:
        session = _session_maker()
    else:
        session = _no_poll_session_maker()
    return session


# async support
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# TODO: refactor - mode to ext module
# TODO: fix - in sync event loop mode force use NullPull
# TODO: fix - make async engine dynamic and valid only for postgresql backend
ASYNC_CONNECTION_STRING = furl()
ASYNC_ENGINE_OPTS_POOLED = settings.DATABASES['default'].get('ASYNC_ENGINE_OPTS_POOLED', None)
ASYNC_ENGINE_OPTS_NON_POOLED = settings.DATABASES['default'].get('ASYNC_ENGINE_OPTS_NON_POOLED', None)

if _ENGINE == 'postgresql':
    ASYNC_CONNECTION_STRING.scheme = 'postgresql+asyncpg'

    # engine options
    if ASYNC_ENGINE_OPTS_POOLED is None:
        ASYNC_ENGINE_OPTS_POOLED = {
            'pool_recycle': 3600,
            'pool_size': 50,
            'max_overflow': 50
        }
    if ASYNC_ENGINE_OPTS_POOLED is None:
        ASYNC_ENGINE_OPTS_POOLED = {}

    if ASYNC_ENGINE_OPTS_NON_POOLED is None:
        ASYNC_ENGINE_OPTS_NON_POOLED = {}

    ASYNC_ENGINE_OPTS_POOLED['connect_args'] = {"server_settings": {"jit": "off"}}  # ОЧЕНЬ ВАЖНО!!!
    ASYNC_ENGINE_OPTS_NON_POOLED['connect_args'] = {"server_settings": {"jit": "off"}}  # ОЧЕНЬ ВАЖНО!!!
elif _ENGINE == 'sqlite':
    ASYNC_CONNECTION_STRING.scheme = 'sqlite+aiosqlite'
    if ASYNC_ENGINE_OPTS_POOLED is None:
        ASYNC_ENGINE_OPTS_POOLED = {}

    if ASYNC_ENGINE_OPTS_NON_POOLED is None:
        ASYNC_ENGINE_OPTS_NON_POOLED = {}
else:
    raise ServerError('Could not initialize async session engine')

ASYNC_CONNECTION_STRING.username = _USER
ASYNC_CONNECTION_STRING.password = _PASS
if _HOST is not None:
    ASYNC_CONNECTION_STRING.host = _HOST
else:
    ASYNC_CONNECTION_STRING.host = ''
if _NAME is not None:
    ASYNC_CONNECTION_STRING.path.add(_NAME)
if _PORT is not None:
    ASYNC_CONNECTION_STRING.port = int(_PORT)
if _OPTS is not None:
    ASYNC_CONNECTION_STRING.args.update(_OPTS)
# TODO: check on asyncpg and place properly
# ASYNC_CONNECTION_STRING.args['prepared_statement_cache_size'] = 10
ASYNC_CONNECTION_STRING = ASYNC_CONNECTION_STRING.url
logger.info(f'ASYNC_CONNECTION_STRING{ASYNC_CONNECTION_STRING}')
logger.info(f'database. ASYNC options[pooled =  True]: engine_opts={ASYNC_ENGINE_OPTS_POOLED}'
            f', session_opts={_SESSION_OPTS}')

logger.info(f'database. ASYNC options[pooled = False]: engine_opts={ASYNC_ENGINE_OPTS_NON_POOLED}'
            f', session_opts={_SESSION_OPTS}')

_async_engine = create_async_engine(
    ASYNC_CONNECTION_STRING,  **ASYNC_ENGINE_OPTS_POOLED
)

_async_engine_nopool = create_async_engine(ASYNC_CONNECTION_STRING, poolclass=NullPool, **ASYNC_ENGINE_OPTS_NON_POOLED)

async_session_factory = sessionmaker(bind=_async_engine, expire_on_commit=False, class_=AsyncSession, **_SESSION_OPTS)
async_session_factory_noloop = sessionmaker(bind=_async_engine_nopool, expire_on_commit=False, class_=AsyncSession, **_SESSION_OPTS)
