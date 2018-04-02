# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


from django.conf import settings

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from lamb.rest.exceptions import ServerError


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
        echo=getattr(settings, 'LAMB_SQLALCHEMY_ECHO', False),
        pool_recycle=3600
    )
except KeyError as e:
    raise ServerError('Database session constructor failed to get database params')


DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata
metadata.bind = _engine


def lamb_db_session_maker():
    """ Constructor for database sqlalchemy sessions
    :return: Instance of session object
    :rtype: sqlalchemy.orm.Session
    """
    maker = sessionmaker(bind=_engine)
    session = maker()
    return session
