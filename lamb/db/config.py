from __future__ import annotations

import dataclasses
import json
import logging
from collections.abc import Callable
from typing import Any

import furl

from lamb.exc import ImproperlyConfiguredError, ServerError
from lamb.json.encoder import JsonEncoder
from lamb.utils import get_settings_value
from lamb.utils.core import compact, masked_url

try:
    import orjson
except ImportError:
    orjson = None

__all__ = ["LambDbConfig", "parse_django_config"]

logger = logging.getLogger(__name__)


class InvalidDatabaseConfigError(ImproperlyConfiguredError):
    _message = "Could not initialize database config"


auto = object()

_encoder = JsonEncoder()


def _json_serializer(obj) -> str | bytes:
    if orjson is not None:
        return orjson.dumps(
            obj,
            default=_encoder.default,
            option=orjson.OPT_PASSTHROUGH_DATETIME | orjson.OPT_NON_STR_KEYS,
        ).decode("utf-8")
    else:
        return json.dumps(obj, default=_encoder.default, ensure_ascii=False)


@dataclasses.dataclass(frozen=True)
class LambDbConfig:
    driver: str | None = None
    async_driver: str | None = None
    host: str | list[str] | None = None
    port: int | list[int] | None = None
    db_name: str | None = None
    username: str | None = None
    password: str | None = None
    app_name: str | None = auto

    connect_options: Callable | dict[str, Any] | None = None
    session_options: Callable | dict[str, Any] | None = None
    engine_options: Callable | dict[str, Any] | None = None

    aconnect_options: Callable | dict[str, Any] | None = None
    asession_options: Callable | dict[str, Any] | None = None
    aengine_options: Callable | dict[str, Any] | None = None

    def __post_init__(self):
        # TODO: check only for postrgesql
        if isinstance(self.host, list) and len(self.host) == 1:
            object.__setattr__(self, "host", self.host[0])

        if isinstance(self.port, list) and len(self.port) == 1:
            object.__setattr__(self, "port", self.port[0])

        if self.app_name == auto:
            app_name = get_settings_value("LAMB_APP_NAME", default=None)
            object.__setattr__(self, "app_name", app_name)

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

        logger.debug(f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] driver: {_driver}")
        if _driver in ["sqlite+pysqlite", "sqlite+pysqlcipher", "sqlite+aiosqlite"] and (
            self.username is None or len(self.username) == 0
        ):
            logger.warning(f"<{self.__class__.__name__}>. patching invalid username for sqlite")
            result.username = ""

        _connect_options = self.connect_options_(sync=sync, pooled=pooled)
        if _connect_options is not None and len(_connect_options) > 0:
            result.args.update(_connect_options)

        logger.debug(f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] connection_string_: {masked_url(result)}")
        return result.url

    # connect options
    def connect_options_(self, sync: bool, pooled: bool) -> dict[str, Any]:
        _options = self.connect_options if sync else self.aconnect_options

        if _options is None:
            # default
            result = {}
            logger.debug(
                f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] connect_options_: {result=}, mode=DEFAULTS,"
            )
        elif isinstance(_options, dict):
            result = _options
            logger.debug(f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] connect_options_: {result=}, mode=DICT")
        elif callable(_options):
            result = _options(self, sync, pooled)
            logger.debug(
                f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] connect_options_: {result=}, mode=CALLABLE"
            )
        else:
            raise InvalidDatabaseConfigError

        return result

    # session options
    def session_options_(self, sync: bool, pooled: bool) -> dict[str, Any]:
        _options = self.session_options if sync else self.asession_options

        if _options is None:
            # default
            result = {}
            logger.debug(
                f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] session_options_: {result=}, mode=DEFAULTS"
            )
        elif isinstance(_options, dict):
            result = _options
            logger.debug(f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] session_options_: {result=}, mode=DICT")
        elif callable(_options):
            result = _options(self, sync, pooled)
            logger.debug(
                f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] session_options_: {result=}, mode=CALLABLE"
            )
        else:
            raise InvalidDatabaseConfigError

        return result

    # engine options
    def engine_options_(self, sync: bool, pooled: bool) -> dict[str, Any]:
        # early returns
        # TODO: support merging strategy with default implementation
        # TODO: remove dict support as not required
        _options = self.engine_options if sync else self.aengine_options

        if _options is None:
            # extract driver
            _driver = self.driver if sync else self.async_driver

            if "+" in _driver:
                _driver = _driver.rpartition("+")[2]

            result: dict[str, Any] = {"json_serializer": _json_serializer}

            if _driver == "psycopg2":
                result.update(
                    {
                        "insertmanyvalues_page_size": 10000,
                        "connect_args": compact({"connect_timeout": 5, "application_name": self.app_name}),
                    }
                )
                if pooled:
                    result.update({"pool_recycle": 3600, "pool_size": 5, "max_overflow": 10})
                    if self.multi_host:
                        result.update({"pool_pre_ping": True})
            elif _driver == "asyncpg":
                result.update(
                    {
                        "connect_args": {
                            "server_settings": compact(
                                {
                                    "jit": "off",
                                    "application_name": self.app_name,
                                }
                            ),
                            "timeout": 5,
                        }
                    }
                )
                if pooled:
                    result.update({"pool_size": 100, "max_overflow": 100})
                    if self.multi_host:
                        result.update({"pool_pre_ping": True})
            logger.debug(
                f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] engine_options_: {result=}, mode=DEFAULTS, driver={_driver}"
            )
        elif isinstance(_options, dict):
            result = _options
            logger.debug(f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] engine_options_: {result=}, mode=DICT")
        elif callable(_options):
            result = _options(self, sync, pooled)
            logger.debug(f"<{self.__class__.__name__}>. [{sync=}, {pooled=}] engine_options_: {result=}, mode=CALLABLE")
        else:
            raise InvalidDatabaseConfigError

        return result


def parse_django_config() -> dict[str, LambDbConfig]:
    from django.conf import settings

    result = {}

    for key, dct in settings.DATABASES.items():
        _engine = dct["ENGINE"]
        _engine = _engine.rpartition(".")[2]
        if _engine == "sqlite3":
            _engine = "sqlite"

        result[key] = LambDbConfig(
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


# deprecation compatibility
Config = LambDbConfig
