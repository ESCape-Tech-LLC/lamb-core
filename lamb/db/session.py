from __future__ import annotations

import logging
import warnings
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from lamb.db.config import Config, parse_django_config
from lamb.exc import ServerError
from lamb.utils import get_settings_value

__all__ = [
    "DeclarativeBase",
    "metadata",
    "lamb_db_session_maker",
    "declarative_base",
    "create_engine",
    "create_async_engine",
    "get_engine",
    "get_declarative_base",
    "get_metadata",
]

logger = logging.getLogger(__name__)


# load database configs
# TODO: modify to handle config dict version - cause on start LAMB_DB_CONFIG is not exist
_LAMB_DB_CONFIG = get_settings_value("LAMB_DB_CONFIG", req_type=dict, default=None)

_configs_registry: dict[str, Config] = {}
if _LAMB_DB_CONFIG is None:
    warnings.warn(
        "parsing old style django DATABASE config, should migrate to LAMB_DB_CONFIG",
        DeprecationWarning,
        stacklevel=2,
    )
    _configs_registry = parse_django_config()
else:
    for _db_key, raw_config in _LAMB_DB_CONFIG.items():
        if isinstance(raw_config, Config):
            _configs_registry[_db_key] = raw_config
        else:
            _configs_registry[_db_key] = Config(**raw_config)

# engines registry
_engines_registry: dict[tuple[str, bool, bool], Engine | AsyncEngine] = {}


def get_engine(db_key: str, pooled: bool, sync: bool) -> Engine | AsyncEngine:
    registry_key = (db_key, pooled, sync)
    if registry_key in _engines_registry:
        return _engines_registry[registry_key]

    if db_key not in _configs_registry:
        logger.critical(f"unknown db key: {db_key}. known registry - {_configs_registry}")
        raise ServerError("Database session constructor failed to get database params")

    db_config: Config = _configs_registry[db_key]
    connection_string = db_config.connection_string_(sync=sync, pooled=pooled)
    engine_options = db_config.engine_options_(sync=sync, pooled=pooled)

    if not pooled:
        engine_options["poolclass"] = NullPool

    if sync:
        result = create_engine(url=connection_string, **engine_options)
    else:
        result = create_async_engine(url=connection_string, **engine_options)

    _engines_registry[registry_key] = result

    return result


# session makers
_maker_registry: dict[tuple[str, bool, bool], sessionmaker] = {}


def get_session_maker(db_key: str = "default", pooled: bool = True, sync: bool = True):
    key = (db_key, pooled, sync)
    if key in _maker_registry:
        return _maker_registry[key]

    database_config: Config = _configs_registry[db_key]
    engine = get_engine(db_key, pooled, sync)
    session_options = database_config.session_options_(sync=sync, pooled=pooled)

    if sync:
        result = sessionmaker(bind=engine, **session_options)
    else:
        result = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession, **session_options)

    _maker_registry[key] = result

    return result


# metadata
_declarative_registry: dict[str, Any] = {}


def get_declarative_base(db_key: str, pooled: bool, sync: bool):
    components = ["PT" if pooled else "PF", "ST" if sync else "SF", "_".join(db_key.split())]
    cls_name = f"DeclarativeBase_{'_'.join(components)}"
    if cls_name not in _declarative_registry:
        _result = declarative_base(name=cls_name)
        _metadata = _result.metadata
        _metadata.bind = get_engine(db_key, pooled=pooled, sync=sync)
        _declarative_registry[cls_name] = _result
    logger.debug(f"did return declarative: {cls_name}")
    return _declarative_registry[cls_name]


def get_metadata(db_key: str, pooled: bool, sync: bool):
    _declarative = get_declarative_base(db_key, pooled, sync)
    return _declarative.metadata


# defaults - compatibility mode
DeclarativeBase = get_declarative_base("default", True, True)
metadata = DeclarativeBase.metadata


def lamb_db_session_maker(pooled: bool = True, db_key: str = "default", sync: bool = True) -> Session | AsyncSession:
    """Constructor for database sqlalchemy sessions"""
    maker = get_session_maker(db_key=db_key, pooled=pooled, sync=sync)
    return maker()
