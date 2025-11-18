import json
import logging
from functools import wraps

from asgiref.sync import iscoroutinefunction
from django.conf import settings

from lamb.json import JsonEncoder, JsonResponse
from lamb.service.redis.config import RedisConfig

logger = logging.getLogger(__name__)


__all__ = ["rejson_cached", "json_cached"]


def json_cached(cache_key: str, ttl: int = 15 * 60, redis_conf_name: str = "cache"):
    """Base Redis/Valkey cache decorator with custom json encoding

    - sync/async compatible
    - can be used with function-based view directly
    - can be used with class-based views via `django.utils.decorators.method_decorator`

    usage::

        from lamb.service.redis.cache import json_cached


        @json_cached(cache_key="handbooks", ttl=15 * 60, redis_conf_name="cache")
        async def some_view(request):
            return {"some_key": 1}

    usage::

        from django.utils.decorators import method_decorator
        from lamb.service.redis.cache import json_cached


        @rest_allowed_http_methods(["GET"])
        class ConfigListView(RestView):
            @method_decorator(json_cached(cache_key="handbooks", ttl=15 * 60, redis_conf_name="cache"))
            def get(self, _: MessengerRequest):
                result = JsonResponse.encode_object(get_visible_configs())
                return result

    usage::

        from django.utils.decorators import method_decorator
        from lamb.service.redis.cache import json_cached


        @a_rest_allowed_http_methods(["GET"])
        class SomeView(LolaRestView):
            async def get(self, request: LambRequest, name: str):
                # check name
                name = validate_not_empty(name).lower()
                cache_key = f"some_cache:{name}"

                @json_cached(cache_key=cache_key, ttl=5 * 3)
                async def _inner(*args, **kwargs):
                    return (await self.db_default.execute(select(Book))).scalars().all()

                return await _inner(request, name)

    """

    # TODO: add support for callable cache_key with context of request and args

    def decorator(view_func):
        if iscoroutinefunction(view_func):

            async def _view_wrapper(request, *args, **kwargs):
                # check cache
                redis_conf: RedisConfig = settings.LAMB_REDIS_CONFIG[redis_conf_name]
                r = await redis_conf.aredis()
                if cached_data := await r.get(cache_key):
                    logger.info(f"json_cached: cache hit - KEY={cache_key}", extra={"key": cache_key})
                    cached_data = json.loads(cached_data)
                    return JsonResponse(cached_data)

                # store to redis and return response
                response = await view_func(request, *args, **kwargs)
                await r.set(name=cache_key, value=json.dumps(response, cls=JsonEncoder), ex=ttl)
                logger.info(
                    f"json_cached: cache add - KEY={cache_key}, TTL={ttl}", extra={"key": cache_key, "ttl": ttl}
                )
                return JsonResponse(response)
        else:

            def _view_wrapper(request, *args, **kwargs):
                # check cache
                redis_conf: RedisConfig = settings.LAMB_REDIS_CONFIG[redis_conf_name]
                r = redis_conf.redis()
                if cached_data := r.get(cache_key):
                    logger.info(f"json_cached: cache hit - KEY={cache_key}", extra={"key": cache_key})
                    cached_data = json.loads(cached_data)
                    return JsonResponse(cached_data)

                # store to redis and return response
                response = view_func(request, *args, **kwargs)
                r.set(name=cache_key, value=json.dumps(response, cls=JsonEncoder), ex=ttl)
                logger.info(
                    f"json_cached: cache add - KEY={cache_key}, TTL={ttl}", extra={"key": cache_key, "ttl": ttl}
                )
                return JsonResponse(response)

        return wraps(view_func)(_view_wrapper)

    return decorator


def rejson_cached(cache_key: str, ttl: int = 15 * 60, redis_conf_name: str = "cache"):
    """Version of cache with Redis/Valkey instance that supports JSON operations"""

    _encoder = JsonEncoder()

    def decorator(view_func):
        if iscoroutinefunction(view_func):

            async def _view_wrapper(request, *args, **kwargs):
                # check cache
                redis_conf: RedisConfig = settings.LAMB_REDIS_CONFIG[redis_conf_name]
                r = await redis_conf.aredis()
                rj = r.json(encoder=_encoder)

                if cached_data := await rj.get(cache_key):
                    logger.info(f"rejson_cached: cache hit - KEY={cache_key}", extra={"key": cache_key})
                    return JsonResponse(cached_data)

                # store to redis and return response
                response = await view_func(request, *args, **kwargs)
                await rj.set(name=cache_key, path=".", obj=response)
                await r.expire(name=cache_key, time=ttl)
                logger.debug(
                    f"rejson_cached: cache add- KEY={cache_key}, TTL={ttl}", extra={"key": cache_key, "ttl": ttl}
                )
                return JsonResponse(response)
        else:

            def _view_wrapper(request, *args, **kwargs):
                # check cache
                redis_conf: RedisConfig = settings.LAMB_REDIS_CONFIG[redis_conf_name]
                r = redis_conf.redis()
                rj = r.json(encoder=_encoder)
                if cached_data := rj.get(cache_key):
                    logger.info(f"rejson_cached: cache hit - KEY={cache_key}", extra={"key": cache_key})
                    return JsonResponse(cached_data)

                # store to redis and return response
                response = view_func(request, *args, **kwargs)
                rj.set(name=cache_key, path=".", obj=response)
                r.expire(name=cache_key, time=ttl)
                logger.debug(
                    f"rejson_cached: cache add- KEY={cache_key}, TTL={ttl}", extra={"key": cache_key, "ttl": ttl}
                )
                return JsonResponse(response)

        return wraps(view_func)(_view_wrapper)

    return decorator
