# -*- coding: utf-8 -*-

import time
import logging
import redis
import json
import re
import dataclasses

from datetime import datetime
from typing import List, Tuple, Dict
from lamb.exc import *
from lamb.utils import dpath_value

__all__ = ['redis_rate_check_pipelined', 'redis_rate_check_lua', 'redis_rate_clear_lua', 'RateLimit']

logger = logging.getLogger(__name__)


def _check_limits(limits: List[Tuple[int, int]]) -> Dict[int, int]:
    limits_dict: Dict[int, int] = {}
    for limit, duration in limits:
        if duration <= 0:
            logger.error(f'invalid duration received: {duration}')
            raise ImproperlyConfiguredError
        if limit <= 0:
            logger.error(f'invalid limit received: {limit}')
            raise ImproperlyConfiguredError

        if duration not in limits_dict:
            limits_dict[duration] = limit
        limits_dict[duration] = min(limits_dict[duration], limit)
    logger.debug(f'limits normalized: {limits} -> {limits_dict}')
    return limits_dict


def _hash_marked_bucket_name(value: str) -> str:
    """ Add hash_tag mark to bucket name of not exist already"""
    if not re.match(r'^(.*?)\{(.+?)\}(.*?)$', value):
        return f'{{{value}}}'
    else:
        return value


def redis_rate_check_pipelined(conn: redis.Redis, bucket_name_base: str, limits: List[Tuple[int, int]] = list()):
    # check and sort limits
    logger.debug(f'start rate check pipelined: {conn, bucket_name_base, limits}')
    limits_dict: Dict[int, int] = _check_limits(limits)

    # check limits
    now = int(time.time())
    pipe = conn.pipeline()
    for duration in sorted(limits_dict.keys(), reverse=True):
        limit = limits_dict[duration]
        time_slot = now // duration
        bucket_name_slot = f'{bucket_name_base}:{duration}:{time_slot}'

        pipe.incr(bucket_name_slot)
        pipe.expire(bucket_name_slot, duration)
        res = pipe.execute()
        logger.info(f'pipeline result: [bucket={bucket_name_slot}, limit={limit}, duration={duration}] -> {res}')
        if res[0] > limit:
            raise ThrottlingError


# lua version
@dataclasses.dataclass(frozen=True)
class RateLimit():
    key: str
    limit: int
    current: int
    duration: int
    time_slot: int

    @property
    def success(self) -> bool:
        return self.current <= self.limit


def _redis_rate_parse_limits(bucket_name_base, limits: List[Tuple[int, int]]) -> List[RateLimit]:
    # check and sort limits
    limits_dict: Dict[int, int] = _check_limits(limits)
    bucket_name_base = _hash_marked_bucket_name(bucket_name_base)

    # repack bucket and limits
    now = int(time.time())

    result = []
    for duration, limit in limits_dict.items():
        time_slot = now // duration
        bucket_name_slot = f'{bucket_name_base}:{duration}:{time_slot}'

        rate_limit = RateLimit(
            key=bucket_name_slot,
            limit=limit,
            current=0,
            duration=duration,
            time_slot=time_slot
        )
        result.append(rate_limit)

    return result


def _redis_rate_parse_response(response: Dict[str, dict]) -> List[RateLimit]:
    result = []
    for key, res in response.items():
        subkey, _, time_slot = key.rpartition(':')
        time_slot = int(time_slot)

        subkey, _, duration = subkey.rpartition(':')
        duration = int(duration)

        current = dpath_value(res, 'current', int)
        limit = dpath_value(res, 'limit', int)

        rate_limit = RateLimit(
            key=key,
            limit=limit,
            current=current,
            duration=duration,
            time_slot=time_slot
        )
        result.append(rate_limit)

    return result


def redis_rate_check_lua(conn: redis.Redis,
                         bucket_name_base: str,
                         limits: List[Tuple[int, int]] = list(),
                         increment: bool = True
                         ) -> List[RateLimit]:
    # check and sort limits
    logger.debug(f'Lua throttling. Start rate check: {conn, bucket_name_base, limits, increment}')
    rate_limits = _redis_rate_parse_limits(bucket_name_base, limits)
    logger.debug(f'Lua throttling. Limits: {rate_limits}')

    # on-demand script create
    if not hasattr(conn, 'redis_rate_check_lua'):
        redis_rate_check_lua_ = '''
        --> arg parse
        local bucket_params = cjson.decode(ARGV[1])
        local increment = tonumber(ARGV[2])
        
        --> local variables
        local bname
        local limit
        local duration
        local current
        
        --> result container
        local result = {}
        
        for idx, bparam in ipairs(bucket_params) do
            bname = bparam[1]
            limit = bparam[2]
            duration = bparam[3] 
            
            --> get current
            current = redis.call('GET', bname)
            
            if (not current) then
                current=0
            else
                current = tonumber(current)
            end
            
            --> check limit reach
            if current < limit then
                if increment == 1 then
                    redis.call('INCR', bname)
                    redis.call('EXPIRE', bname, duration)
                    current = current + 1
                end
            end
            
            --> pack result
            local result_record = {}
            result_record['limit'] = limit
            result_record['current'] = current
            result[bname] = result_record
        end
        return cjson.encode(result)
        '''
        conn.redis_rate_check_lua = conn.register_script(redis_rate_check_lua_)
        logger.info(f'Lua throttling. Script compiled and loaded: {conn.redis_rate_check_lua}')

    # check limits
    increment = 1 if increment else 0
    json_args = [[rl.key, rl.limit, rl.duration] for rl in rate_limits]
    json_args = json.dumps(json_args)
    logger.debug(f'Lua throttling. Calling redis_rate_check_lua: keys={bucket_name_base}, args={json_args, increment}')
    res = conn.redis_rate_check_lua(keys=[bucket_name_base], args=[json_args, increment])
    logger.info(f'Lua throttling. Response binary: {res}')

    # analyse and wrap results
    try:
        res = json.loads(res)
        logger.debug(f'Lua throttling. Response json: {res}')
        res_rate_limits = _redis_rate_parse_response(res)
        logger.debug(f'Lua throttling. Response parsed: {res_rate_limits}')
        if any([not rl.success for rl in res_rate_limits]):
            raise ThrottlingError(limits=res_rate_limits)
        return res_rate_limits
    except ApiError:
        raise
    except Exception as e:
        raise ExternalServiceError from e


def redis_rate_clear_lua(conn: redis.Redis,
                         bucket_name_base: str,
                         limits: List[Tuple[int, int]] = list(),
                         increment: bool = True
                         ):
    # check and sort limits
    logger.debug(f'Lua throttling. Start rate clear: {conn, bucket_name_base, limits, increment}')
    rate_limits = _redis_rate_parse_limits(bucket_name_base, limits)
    logger.info(f'Lua throttling. Limits to clear: {rate_limits}')

    keys = [rl.key for rl in rate_limits]
    logger.debug(f'Lua throttling. Keys to remove: {keys}')
    conn.delete(*keys)
    logger.info(f'Lua throttling. Did remove keys: {keys}')
