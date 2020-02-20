# -*- coding: utf-8 -*-

import time
import logging
import redis
import json
import re

from typing import List, Tuple, Dict
from lamb.exc import *

__all__ = ['redis_rate_check_pipelined', 'redis_rate_check_lua']

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


def redis_rate_check_lua(conn: redis.Redis, bucket_name_base: str, limits: List[Tuple[int, int]] = list()):
    # check and sort limits
    logger.debug(f'start rate check lua: {conn, bucket_name_base, limits}')
    limits_dict: Dict[int, int] = _check_limits(limits)
    bucket_name_base = _hash_marked_bucket_name(bucket_name_base)

    # repack bucket and limits
    now = int(time.time())

    bucket_args: List[Tuple[str, int, int]] = []
    for duration, limit in limits_dict.items():
        time_slot = now // duration
        bucket_name_slot = f'{bucket_name_base}:{duration}:{time_slot}'
        # bucket_dict[bucket_name_slot] = (limit, duration)
        bucket_args.append((bucket_name_slot, limit, duration))
    logger.info(f'bucket args: {bucket_args}')
    # on-demand script create
    if not hasattr(conn, 'redis_rate_check_lua'):
        redis_rate_check_lua_ = '''
        local bucket_params = cjson.decode(ARGV[1])
        
        local bname
        local limit
        local duration
        local current
        
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
            
            if current >= limit then
                return '"failed"'
            else
                redis.call('INCR', bname)
                redis.call('EXPIRE', bname, duration)
                result[bname] = current + 1
            end
        end
        return cjson.encode(result)
        '''
        conn.redis_rate_check_lua = conn.register_script(redis_rate_check_lua_)
        logger.info(f'script loaded: {conn.redis_rate_check_lua}')

    # check limits
    json_args = json.dumps(bucket_args)
    logger.debug(f'calling redis_rate_check_lua: keys={bucket_name_base}, args={json_args}')
    res = conn.redis_rate_check_lua(keys=[bucket_name_base], args=[json_args])
    logger.info(f'response binary: {res}')

    try:
        res = json.loads(res)
        logger.debug(f'response json: {res}')
        if res == 'failed':
            raise ThrottlingError
    except ApiError:
        raise
    except Exception as e:
        raise ExternalServiceError from e
