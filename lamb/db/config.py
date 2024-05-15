from __future__ import annotations

# -*- coding: utf-8 -*-
__author__ = "KoNEW"

import json
import logging
import dataclasses
from typing import Any, Dict, List, Union, Callable, Optional

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
    host: Optional[str | List[str]] = None
    port: Optional[int | List[int]] = None
    db_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    connect_options: Optional[Union[Callable, Dict[str, Any]]] = None
    session_options: Optional[Union[Callable, Dict[str, Any]]] = None
    engine_options: Optional[Union[Callable, Dict[str, Any]]] = None

    aconnect_options: Optional[Union[Callable, Dict[str, Any]]] = None
    asession_options: Optional[Union[Callable, Dict[str, Any]]] = None
    aengine_options: Optional[Union[Callable, Dict[str, Any]]] = None

    def __post_init__(self):
        # TODO: check only for postrgesql
        if isinstance(self.host, list) and len(self.host) == 1:
            object.__setattr__(self, "host", self.host[0])

        if isinstance(self.port, list) and len(self.port) == 1:
            object.__setattr__(self, "port", self.port[0])

    # properties
    @property
    def multi_host(self) -> bool:
        return isinstance(self.host, list) and len(self.host) > 1

    # connection string
    def connection_string_(self, sync: bool, pooled: bool) -> str:
        _driver = self.driver if sync else self.async_driver

        if _driver is None:
            logger.critical(f"<{self.__class__.__name__}>. invalid driver info on connection: {sync, pooled=}")
            raise InvalidDatabaseConfigError

        result = furl.furl()
        result.scheme = _driver

        # multi host and port support
        host = self.host or ""
        if isinstance(host, list):
            result.args["host"] = ",".join(host)
        else:
            result.host = host

        if isinstance(self.port, list):
            result.args["port"] = ",".join([str(p) for p in self.port])
        elif self.port is not None:
            result.port = self.port

        # other params
        if self.username is not None:
            result.username = self.username
        if self.password is not None:
            result.password = self.password
        if self.db_name is not None:
            result.path.add(self.db_name)

        logger.debug(f"<{self.__class__.__name__}>. driver would be used: {_driver}")
        if _driver in ["sqlite+pysqlite", "sqlite+pysqlcipher", "sqlite+aiosqlite"] and (
            self.username is None or len(self.username) == 0
        ):
            logger.warning(f"<{self.__class__.__name__}>. patching invalid username for sqlite")
            result.username = ""

        _connect_options = self.connect_options_(sync=sync, pooled=pooled)
        if _connect_options is not None and len(_connect_options) > 0:
            result.args.update(_connect_options)

        logger.debug(
            f"<{self.__class__.__name__}>. connection string constructed: {sync, pooled=} -> {masked_url(result)}"
        )
        return result.url

    # connect options
    def connect_options_(self, sync: bool, pooled: bool) -> Dict[str, Any]:
        _options = self.connect_options if sync else self.aconnect_options

        if _options is None:
            # default
            result = {}
            logger.debug(
                f"<{self.__class__.__name__}>. connection options constructed from DEFAULT: {sync, pooled=} -> {result}"
            )
            # return {}
        elif isinstance(_options, dict):
            result = _options
            logger.debug(
                f"<{self.__class__.__name__}>. connection options constructed from DICT: {sync, pooled=} -> {result}"
            )
        elif callable(_options):
            result = _options(self, sync, pooled)
            logger.debug(
                f"<{self.__class__.__name__}>. "
                f"connection options constructed from CALLABLE: {sync, pooled=} -> {result}"
            )
            # return _options(self, sync, pooled)
        else:
            raise InvalidDatabaseConfigError

        return result

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
                        "insertmanyvalues_page_size": 10000,
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
            logger.debug(
                f"<{self.__class__.__name__}>. "
                f"engine options constructed from DEFAULT: {sync, pooled, _driver=} -> {result}"
            )
            # return result
        elif isinstance(_options, dict):
            result = _options
            logger.debug(
                f"<{self.__class__.__name__}>. engine options constructed from DICT: {sync, pooled=} -> {result}"
            )
            # return _options
        elif callable(_options):
            result = _options(self, sync, pooled)
            logger.debug(
                f"<{self.__class__.__name__}>. engine options constructed from CALLABLE: {sync, pooled=} -> {result}"
            )
            # return _options(self, sync, pooled)
        else:
            raise InvalidDatabaseConfigError

        return result


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
            username=dct["USER"],
            password=dct["PASSWORD"],
            host=dct["HOST"],
            port=dct.get("PORT", None),
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
