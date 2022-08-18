from __future__ import annotations

# -*- coding: utf-8 -*-
__author__ = "KoNEW"

import json
import logging
import dataclasses
from typing import Any, Dict, Union, Callable, Optional

# Lamb Framework
from lamb.exc import ServerError, ImproperlyConfiguredError
from lamb.utils import masked_url

import furl

__all__ = ["Config", "parse_django_config"]

logger = logging.getLogger(__name__)


class InvalidDatabaseConfigError(ImproperlyConfiguredError):
    _message = "Could not initialize database config"


@dataclasses.dataclass(frozen=True)
class Config:
    # TODO: check and validate multihost connections
    driver: Optional[str] = None
    async_driver: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    db_name: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None

    connect_options: Optional[Union[Callable, Dict[str, Any]]] = None
    session_options: Optional[Union[Callable, Dict[str, Any]]] = None
    engine_options: Optional[Union[Callable, Dict[str, Any]]] = None

    aconnect_options: Optional[Union[Callable, Dict[str, Any]]] = None
    asession_options: Optional[Union[Callable, Dict[str, Any]]] = None
    aengine_options: Optional[Union[Callable, Dict[str, Any]]] = None

    # connection string
    def connection_string_(self, sync: bool, pooled: bool) -> str:
        _driver = self.driver if sync else self.async_driver

        if _driver is None:
            logger.critical(f"Attempt to access connection string without driver info: {sync, pooled=}")
            raise InvalidDatabaseConfigError

        result = furl.furl()
        result.scheme = _driver
        result.host = self.host or ""
        if self.user is not None:
            result.username = self.user
        if self.password is not None:
            result.password = self.password
        if self.port is not None:
            result.port = self.port
        if self.db_name is not None:
            result.path.add(self.db_name)

        logger.info(f"driver: {_driver}")
        if _driver in ["sqlite+pysqlite", "sqlite+pysqlcipher", "sqlite+aiosqlite"] and (
            self.user is None or len(self.user) == 0
        ):
            logger.warning("patching invalid username for sqlite")
            result.username = ""

        _connect_options = self.connect_options_(sync=sync, pooled=pooled)
        if _connect_options is not None and len(_connect_options) > 0:
            result.args.update(_connect_options)

        logger.info(f"connection string constructed: {sync, pooled=} -> {masked_url(result)}")
        return result.url

    # connect options
    def connect_options_(self, sync: bool, pooled: bool) -> Dict[str, Any]:
        _options = self.connect_options if sync else self.aconnect_options

        if _options is None:
            # default
            return {}
        elif callable(_options):
            return _options(self, sync, pooled)
        elif isinstance(_options, dict):
            return _options
        else:
            raise InvalidDatabaseConfigError

    # session options
    def session_options_(self, sync: bool, pooled: bool) -> Dict[str, Any]:
        _options = self.session_options if sync else self.asession_options

        if _options is None:
            # default
            return {}
        elif isinstance(_options, dict):
            return _options
        elif callable(_options):
            return _options(self, sync, pooled)
        else:
            raise InvalidDatabaseConfigError

    # engine options
    def engine_options_(self, sync: bool, pooled: bool) -> Dict[str, Any]:
        # early returns
        _options = self.engine_options if sync else self.aengine_options

        if _options is None:
            # Lamb Framework
            from lamb.json.encoder import JsonEncoder  # TODO: check move to top level

            # extract driver
            _driver = self.driver if sync else self.async_driver

            if "+" in _driver:
                _driver = _driver.rpartition("+")[2]

            result = {"json_serializer": lambda obj: json.dumps(obj, cls=JsonEncoder, ensure_ascii=False)}

            if _driver == "psycopg2":
                result.update(
                    {
                        "executemany_mode": "values",
                        "executemany_values_page_size": 10000,
                        "executemany_batch_page_size": 500,
                        "connect_args": {"connect_timeout": 5},
                    }
                )
                if pooled:
                    result.update({"pool_recycle": 3600, "pool_size": 5, "max_overflow": 10})
            elif _driver == "asyncpg":
                result.update(
                    {
                        "connect_args": {
                            "server_settings": {"jit": "off"},
                            "timeout": 5,
                        }
                    }
                )
                if pooled:
                    result.update({"pool_size": 50, "max_overflow": 50})
                pass
            logger.debug(f"default engine options: {self, sync, pooled, _driver=} -> {result}")
            return result
        elif isinstance(_options, dict):
            return _options
        elif callable(_options):
            return _options(self, sync, pooled)
        else:
            raise InvalidDatabaseConfigError


def parse_django_config() -> Dict[str, Config]:
    from django.conf import settings

    result = {}

    for key, dct in settings.DATABASES.items():
        _engine = dct["ENGINE"]
        _engine = _engine.rpartition(".")[2]
        if _engine == "sqlite3":
            _engine = "sqlite"

        result[key] = Config(
            driver=_engine,
            async_driver=None,
            db_name=dct["NAME"],
            user=dct["USER"],
            password=dct["PASSWORD"],
            host=dct["HOST"],
            port=dct["PORT"],
            connect_options=dct.get("CONNECT_OPTS", None),
            session_options=dct.get("SESSION_OPTS", None),
            engine_options=None,
            aconnect_options=dct.get("CONNECT_OPTS", None),
            asession_options=dct.get("SESSION_OPTS", None),
            aengine_options=None,
        )

        if (
            "ENGINE_OPTS_POOLED" in dct
            or "ENGINE_OPTS_NON_POOLED" in dct
            or "ASYNC_ENGINE_OPTS_POOLED" in dct
            or "ASYNC_ENGINE_OPTS_NON_POOLED" in dct
        ):
            logger.warning("Old style config detailed configs not supported, migrate to modern version")
            raise ServerError("Could not initialize database configs")

    return result
