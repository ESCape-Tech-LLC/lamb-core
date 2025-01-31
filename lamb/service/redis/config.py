from __future__ import annotations

import dataclasses
import enum
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import furl
import redis
import redis.asyncio as redis_asyncio

# Lamb Framework
from lamb.exc import ImproperlyConfiguredError
from lamb.utils.core import lazy
from lamb.utils.transformers import tf_list_int, tf_list_string, transform_string_enum
from lamb.utils.validators import v_opt_string, validate_range

logger = logging.getLogger(__name__)

__all__ = ["Mode", "RedisConfig"]


TS = TypeVar("TS", redis.sentinel.Sentinel, redis_asyncio.sentinel.Sentinel)


@enum.unique
class Mode(str, enum.Enum):
    GENERIC = "GENERIC"
    SENTINEL = "SENTINEL"
    CLUSTER_101 = "CLUSTER_101"


auto = object()


@dataclasses.dataclass
class RedisConfig:
    """Redis config

    Usage::

        from lamb.service.redis.config import Config, Mode

        LAMB_REDIS_CONFIG = {
            'generic': Config(host='valkey', port=6379, mode=Mode.GENERIC, username=None,
                password='12345', default_db=3),
            'sentinel': Config(host='sentinel', port=26379, mode=Mode.SENTINEL, password='12345',
                sentinel_service_name='avroid',default_db=4),
            'cluster': Config(host='valkey-c-1,valkey-c-2', port=[6379,6379], mode=Mode.CLUSTER_101,
                username=None, password='12345')
        }

        # generic
        gr = LAMB_REDIS_CONFIG['generic'].redis()
        gr.set('test_key', 100)
        gr.get('test_key')

        # sentinel master
        m = LAMB_REDIS_CONFIG['sentinel'].redis()
        m.set('test_key_s', 100)
        m.get('test_key_s')

        # sentinel slave node
        s = LAMB_REDIS_CONFIG['sentinel'].redis(sentinel_slave=True)
        s.get('test_key_s')

        # cluster
        c = LAMB_REDIS_CONFIG['cluster'].redis()
        c.set('test_key', 1000)
        c.get('test_key')

        # cluster with override params
        c2 = LAMB_REDIS_CONFIG['cluster'].redis(decode_responses=False)

    """

    # TODO: support for unix domain connection
    # TODO: support for SSL configs
    host: Union[str, List[str]]
    port: Union[int, List[int]] = 6379
    username: Optional[str] = None
    password: Optional[str] = None
    default_db: int = 0
    mode: Mode = Mode.GENERIC
    # sentinel specific
    sentinel_service_name: Optional[str] = None
    sentinel_password: Optional[str] = auto

    def __post_init__(self):
        # normalize formats
        self.host = tf_list_string(self.host)
        self.port = tf_list_int(self.port)
        self.default_db = validate_range(int(self.default_db), min_value=0)
        self.mode = transform_string_enum(self.mode, Mode)
        self.username = v_opt_string(self.username)
        self.password = v_opt_string(self.password)
        self.sentinel_service_name = v_opt_string(self.sentinel_service_name)
        if self.mode == Mode.SENTINEL:
            if self.sentinel_password == auto:
                logger.warning("sentinel_password is auto: use same as underlying nodes")
                self.sentinel_password = self.password
            else:
                self.sentinel_password = v_opt_string(self.sentinel_password)
        # post checks
        if len(self.host) != len(self.port):
            raise ImproperlyConfiguredError("Length of hosts and ports must match")
        if self.mode == Mode.GENERIC and len(self.port) > 1:
            raise ImproperlyConfiguredError(f"Mode={self.mode} supports only one host/port: {self}")
        if self.mode == Mode.SENTINEL and self.sentinel_service_name is None:
            raise ImproperlyConfiguredError(f"Service name required for Sentinel mode: {self}")
        if self.mode == Mode.GENERIC:
            self.host = self.host[0]
            self.port = self.port[0]

        if self.mode == Mode.CLUSTER_101 and self.default_db != 0:
            raise ImproperlyConfiguredError("Cluster mode do not support database configuration")

    # utils
    def _url(
        self,
        host: str,
        port: int,
        scheme: str = "redis",
        username: Optional[str] = None,
        password: Optional[str] = None,
        db: Optional[int] = None,
    ) -> str:
        u = furl.furl()
        u.scheme = scheme.lower()
        u.host = host
        u.port = port
        if _username := username:
            u.user = _username
        if _password := password:
            u.password = _password
        if _db := db:
            u.path.add(str(_db))
        return u.url

    @lazy
    def url(self) -> str:
        """Construct simple url for redis"""
        return self._url(
            host=self.host[0] if isinstance(self.host, list) else self.host,
            port=self.port[0] if isinstance(self.port, list) else self.port,
            scheme="redis",
            username=self.username,
            password=self.password,
            db=self.default_db,
        )

    @lazy
    def _generic_pool(self) -> redis.ConnectionPool:
        return redis.ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.default_db,
            username=self.username,
            password=self.password,
            decode_responses=True,
        )

    def _manager(self, cls: Type[TS]) -> TS:
        sentinels = list(zip(self.host, self.port))
        return cls(
            sentinels=sentinels,
            sentinel_kwargs={"password": self.sentinel_password},
            decode_responses=True,
            password=self.password,
            username=self.username,
            db=self.default_db,
        )

    @lazy
    def _sentinel_manager(self) -> redis.sentinel.Sentinel:
        return self._manager(cls=redis.sentinel.Sentinel)

    @lazy
    def _async_sentinel_manager(self) -> redis_asyncio.sentinel.Sentinel:
        return self._manager(cls=redis_asyncio.sentinel.Sentinel)

    @lazy
    def _cluster(self) -> redis.cluster.RedisCluster:
        return self._get_cluster()

    def _get_cluster(self, **connection_kwargs):
        startup_nodes = list(zip(self.host, self.port))
        startup_nodes = [redis.cluster.ClusterNode(host=h, port=p) for h, p in startup_nodes]
        if "password" not in connection_kwargs:
            connection_kwargs["password"] = self.password
        return redis.cluster.RedisCluster(startup_nodes=startup_nodes, **connection_kwargs)

    # sentinel broker support
    @lazy
    def broker_url(self) -> str:
        match self.mode:
            case Mode.GENERIC:
                return self.url
            case Mode.SENTINEL:
                sentinels = list(zip(self.host, self.port))
                urls = []
                for s in sentinels:
                    u = self._url(
                        host=s[0], port=s[1], username=self.username, password=self.password, scheme="sentinel"
                    )
                    urls.append(u)
                return ";".join(urls)
            case _:
                raise ImproperlyConfiguredError(f"broker_url is not defined on mode: {self.mode}")

    @lazy
    def broker_transport_options(self) -> Dict[str, Any]:
        if self.mode != Mode.SENTINEL:
            return {}
        else:
            return {
                "master_name": self.sentinel_service_name,
                "sentinel_kwargs": {"password": self.sentinel_password},
            }

    # connection
    def redis(
        self,
        **connection_kwargs,
    ) -> Union[redis.Redis, redis.RedisCluster]:
        """Returns corresponding for config Redis instance

        :param connection_kwargs: extra arguments that would be used with underlying connection

        """
        match self.mode:
            case Mode.GENERIC:
                return redis.Redis(connection_pool=self._generic_pool, **connection_kwargs)
            case Mode.SENTINEL:
                sentinel_service_name = connection_kwargs.pop("sentinel_service_name", self.sentinel_service_name)
                sentinel_slave = connection_kwargs.pop("sentinel_slave", False)
                if sentinel_slave:
                    return self._sentinel_manager.slave_for(sentinel_service_name, **connection_kwargs)
                else:
                    return self._sentinel_manager.master_for(sentinel_service_name, **connection_kwargs)
            case Mode.CLUSTER_101:
                if len(connection_kwargs) == 0:
                    # use cached
                    return self._cluster
                else:
                    # ability to override
                    return self._get_cluster(**connection_kwargs)
            case _:
                raise ImproperlyConfiguredError(f"Unsupported Redis mode: {self.mode}")

    async def aredis(self, **connection_kwargs) -> Union[redis_asyncio.Redis, redis_asyncio.RedisCluster]:
        match self.mode:
            case Mode.GENERIC:
                # TODO: discover pool usage in asyncio version
                # TODO: auto decode response
                return redis_asyncio.Redis.from_url(self.url, **connection_kwargs)
            case Mode.SENTINEL:
                sentinel_service_name = connection_kwargs.pop("sentinel_service_name", self.sentinel_service_name)
                sentinel_slave = connection_kwargs.pop("sentinel_slave", False)
                if sentinel_slave:
                    return self._async_sentinel_manager.slave_for(sentinel_service_name, **connection_kwargs)
                else:
                    return self._async_sentinel_manager.master_for(sentinel_service_name, **connection_kwargs)
            # case Mode.CLUSTER_101:
            #     # TODO: implement async cluster
            #     if len(connection_kwargs) == 0:
            #         # use cached
            #         return self._cluster
            #     else:
            #         # ability to override
            #         return self._get_cluster(**connection_kwargs)
            case _:
                raise ImproperlyConfiguredError(f"Unsupported Redis mode: {self.mode}")


# deprecated version - use base RedisConfig
Config = RedisConfig
