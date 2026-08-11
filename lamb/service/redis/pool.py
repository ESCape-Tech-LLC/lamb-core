from __future__ import annotations

import redis
from django.conf import settings
from redis import asyncio as redis_async

from lamb.exc import ProgrammingError
from lamb.service.redis.config import RedisConfig

__all__ = ["get_redis_async", "get_redis_sync"]

# registries
_redis_pool_registry: dict[str, redis_async.ConnectionPool] = {}
_redis_pool_registry_sync: dict[str, redis.ConnectionPool] = {}


# tools
def get_redis_async(key: str) -> redis_async.Redis:
    # TODO: support kwargs with different pools
    if key not in _redis_pool_registry:
        if key not in settings.LAMB_REDIS_CONFIG:
            raise ProgrammingError(f"Key {key} not found in settings.LAMB_REDIS_CONFIG")

        redis_cfg: RedisConfig = settings.LAMB_REDIS_CONFIG[key]
        pool = redis_async.ConnectionPool.from_url(redis_cfg.url, max_connections=10_000)
        _redis_pool_registry[key] = pool
    else:
        pool = _redis_pool_registry[key]

    return redis_async.Redis(connection_pool=pool)


def get_redis_sync(key: str) -> redis.Redis:
    # TODO: support kwargs with different pools
    if key not in _redis_pool_registry_sync:
        if key not in settings.LAMB_REDIS_CONFIG:
            raise ProgrammingError(f"Key {key} not found in settings.LAMB_REDIS_CONFIG")

        redis_cfg: RedisConfig = settings.LAMB_REDIS_CONFIG[key]
        pool = redis.ConnectionPool.from_url(redis_cfg.url, max_connections=10_000)
        _redis_pool_registry_sync[key] = pool
    else:
        pool = _redis_pool_registry_sync[key]

    return redis.Redis(connection_pool=pool)
