import json
import logging
from functools import wraps

from django.conf import settings

from lamb.json import JsonResponse
from lamb.service.redis.config import RedisConfig

logger = logging.getLogger(__name__)


__all__ = ["rejson_cached", "json_cached"]


def json_cached(cache_key: str, ttl: int = 15 * 60, redis_conf_name: str = "cache"):
    """

    Base Redis/Valkey cache decorator

    Usage::

        from django.utils.decorators import method_decorator
        from lamb.service.redis.cache import json_cached


        @rest_allowed_http_methods(["GET"])
        class ConfigListView(RestView):
            @method_decorator(json_cached(cache_key="handbooks", ttl=15 * 60, redis_conf_name="cache"))
            def get(self, _: MessengerRequest):
                result = JsonResponse.encode_object(get_visible_configs())
                return json.loads(result)

    """

    def decorator(func):
        @wraps(func)
        def inner(request, *args, **kwargs):
            # check cache
            endpoint = request.path
            redis_conf: RedisConfig = settings.LAMB_REDIS_CONFIG[redis_conf_name]
            r = redis_conf.redis()
            cached_data = r.get(cache_key)
            if cached_data is not None:
                logger.info(f"json_cached: {endpoint} -> loaded from redis with KEY={cache_key}, TTL={ttl}")
                cached_data = json.loads(cached_data)
                return JsonResponse(cached_data)

            # call function
            response = func(request, *args, **kwargs)

            # store to redis and return response
            r.set(name=cache_key, value=json.dumps(response), ex=ttl)
            logger.debug(f"json_cached: {endpoint} -> did add to redis with KEY={cache_key}, TTL={ttl}")
            return JsonResponse(response)

        return inner

    return decorator


def rejson_cached(cache_key: str, ttl: int = 15 * 60, redis_conf_name: str = "cache"):
    """Use with Redis/Valkey instance that supports JSON operations"""

    def decorator(func):
        @wraps(func)
        def inner(request, *args, **kwargs):
            # check cache
            endpoint = request.path
            redis_conf: RedisConfig = settings.LAMB_REDIS_CONF[redis_conf_name]
            r = redis_conf.redis()
            cached_data = r.json().get(cache_key)
            if cached_data is not None:
                logger.info(f"rejson_cached: {endpoint} -> loaded from redis with KEY={cache_key}, TTL={ttl}")
                return JsonResponse(cached_data)

            # call function
            response = func(request, *args, **kwargs)

            # store to redis and return response
            r.json().set(name=cache_key, path=".", obj=response)
            r.expire(name=cache_key, time=ttl)
            logger.debug(
                f"rejson_cached: {endpoint} -> did add to redis with "
                f"KEY={cache_key}, "
                f"TTL={ttl}, "
                f"MEMORY={r.json().debug('MEMORY', cache_key)}"
            )
            return JsonResponse(response)

        return inner

    return decorator
