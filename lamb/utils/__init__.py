# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


import random
import string
import json
import uuid
import warnings
import logging
import re
import io
import types
import importlib
import functools
import asyncio
import requests
import enum
import sys

from datetime import datetime, date, timedelta
from typing import List, Union, TypeVar, Optional, Dict, Tuple, Any, Callable, BinaryIO
from urllib.parse import urlsplit, urlunsplit, unquote
from collections import OrderedDict
from asgiref.sync import sync_to_async
from PIL import Image as PILImage
from sqlalchemy import asc, desc
from sqlalchemy.orm import Query
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.inspection import inspect
from sqlalchemy import Column
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import ColumnProperty, RelationshipProperty, synonym
from sqlalchemy.orm.attributes import QueryableAttribute, InstrumentedAttribute
from sqlalchemy.ext.declarative import DeclarativeMeta
from django.http import HttpRequest
from django.conf import settings
from PIL import Image as PILImage
from xml.etree import cElementTree

from lamb.exc import InvalidBodyStructureError, InvalidParamTypeError, InvalidParamValueError, ServerError,\
    UpdateRequiredError, ExternalServiceError
from .dpath import dpath_value


__all__ = [
    'LambRequest', 'parse_body_as_json',  'dpath_value', 'string_to_uuid', 'random_string', 'url_append_components', 'clear_white_space',
    'compact_dict', 'compact_list', 'compact',
    'paginated', 'response_paginated', 'response_sorted', 'response_filtered',

    'get_request_body_encoding', 'get_request_accept_encoding',
    'CONTENT_ENCODING_XML', 'CONTENT_ENCODING_JSON', 'CONTENT_ENCODING_MULTIPART',
    'dpath_value',

    'import_class_by_name', 'import_by_name', 'inject_app_defaults',

    'datetime_end', 'datetime_begin',

    'check_device_info_min_versions',

    'list_chunks',

    'DeprecationClassHelper', 'masked_dict', 'timed_lru_cache', 'timed_lru_cache_clear',
    'async_download_resources', 'async_download_images', 'image_convert_to_rgb', 'file_is_svg'
]


logger = logging.getLogger(__name__)


class LambRequest(HttpRequest):
    """ Class used only for proper type hinting in pycharm, not guarantee that properties will exist
    :type lamb_db_session: sqlalchemy.orm.Session | None
    :type lamb_execution_meter: lamb.execution_time.ExecutionTimeMeter | None
    :type lamb_device_info: lamb.types.DeviceInfo | None
    :type lamb_trace_id: str | None
    :type lamb_locale: lamb.types.LambLocale | None
    """
    def __init__(self):
        super(LambRequest, self).__init__()
        self.lamb_db_session = None
        self.lamb_execution_meter = None
        self.lamb_device_info = None
        self.lamb_trace_id = None
        self.lamb_locale = None


# compatibility
VT = TypeVar('VT')


def validated_interval(value: Optional[VT],
                       bottom: VT,
                       top: VT,
                       key: str = None,
                       allow_none: bool = False) -> Optional[VT]:
    from lamb.utils.validators import validate_range
    warnings.warn('validated_interval method is deprecated, use validate_range version',
                  DeprecationWarning, stacklevel=2)
    return validate_range(
        value=value,
        min_value=bottom,
        max_value=top,
        key=key,
        allow_none=allow_none
    )


# parsing
def parse_body_as_json(request: HttpRequest) -> dict:
    """  Parse request object to dictionary as JSON

    :param request: Request object

    :return:  Body parsed as JSON object

    :raises InvalidBodyStructureError: In case of parsing failed or parsed object is not dictionary
    """
    try:
        body = request.body
    except Exception as e:
        raise ServerError('Invalid request object') from e

    try:
        data = json.loads(body)
        if not isinstance(data, dict):
            raise InvalidBodyStructureError('JSON body of request should be represented in a form of dictionary')
        return data
    except ValueError as e:
        raise InvalidBodyStructureError('Could not parse body as JSON object') from e


# reponse utilities
PV = TypeVar('PV', list, Query)


def paginated(data: PV, request: LambRequest) -> dict:
    """ Deprected version of pagination utility

    :param data: Instance of list or query to be paginated
    :param request: Http request
    """
    warnings.warn('paginated method is deprecated, use response_paginated version', DeprecationWarning, stacklevel=2)
    return response_paginated(data, request)


def response_paginated(data: PV, request: LambRequest = None, params: Dict = None, add_extended_query: bool = False) -> dict:
    """ Pagination utility

    Will search for limit/offset params in `request.GET` object and apply it to data, returning
    dictionary that includes info about real offset, limit, total_count, items.

    :param data: Instance of list or query to be paginated
    :param request: Http request (deprecated version)
    :param params: Dictionary with params of pagination
    :param add_extended_query: Flag to add to result extended version of data slice
        (including one more item from begin and and of slice)
    """
    # check params override
    if request is not None and params is None:
        params = request.GET

    # parse omit total
    from lamb.utils.transformers import transform_boolean
    total_omit = dpath_value(params, settings.LAMB_PAGINATION_KEY_OMIT_TOTAL, str,
                              transform=transform_boolean, default=False)

    # parse and check offset
    offset = dpath_value(params, settings.LAMB_PAGINATION_KEY_OFFSET, int, default=0)
    if offset < 0:
        raise InvalidParamValueError('Invalid offset value for pagination',
                                     error_details=settings.LAMB_PAGINATION_KEY_OFFSET)

    # parse and check limit
    limit = dpath_value(params, settings.LAMB_PAGINATION_KEY_LIMIT, int,
                        default=settings.LAMB_PAGINATION_LIMIT_DEFAULT)
    if limit < -1:
        raise InvalidParamValueError('Invalid limit value for pagination',
                                     error_details=settings.LAMB_PAGINATION_KEY_LIMIT)
    if limit > settings.LAMB_PAGINATION_LIMIT_MAX:
        raise InvalidParamValueError('Invalid limit value for pagination - exceed max available',
                                     error_details=settings.LAMB_PAGINATION_KEY_LIMIT)

    # calculate extended values
    extended_additional_count = 0
    if offset > 0:
        extended_offset = offset - 1
        extended_additional_count = extended_additional_count + 1
    else:
        extended_offset = offset

    if limit != -1:
        extended_additional_count = extended_additional_count + 1
        extended_limit = limit + extended_additional_count
    else:
        extended_limit = limit

    # prepare result container
    result = OrderedDict()
    result[settings.LAMB_PAGINATION_KEY_OFFSET] = offset
    result[settings.LAMB_PAGINATION_KEY_LIMIT] = limit

    if isinstance(data, Query):
        # def get_count(q):
        #     # TODO: Add dynamic count function choose based on any join presented in query
        #     # TODO: modify query - returns invalid count in case of join with one-to-many objects
        #     count_q = q.statement.with_only_columns([func.count()]).order_by(None)
        #     count = q.session.execute(count_q).scalar()
        #     return count
        #
        # result[settings.LAMB_PAGINATION_KEY_TOTAL] = get_count(data)
        if not total_omit:
            result[settings.LAMB_PAGINATION_KEY_TOTAL] = data.count()
        else:
            result[settings.LAMB_PAGINATION_KEY_TOTAL] = None

        if limit == -1:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data.offset(offset).all()
        else:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data.offset(offset).limit(limit).all()

        if add_extended_query:
            if extended_limit == -1:
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = data.offset(extended_offset).all()
            else:
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = data.offset(extended_offset)\
                    .limit(extended_limit)\
                    .all()
    elif isinstance(data, list):
        if not total_omit:
            result[settings.LAMB_PAGINATION_KEY_TOTAL] = len(data)
        else:
            result[settings.LAMB_PAGINATION_KEY_TOTAL] = None

        if limit == -1:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data[offset:]
        else:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data[offset: offset + limit]

        if add_extended_query:
            if extended_limit == -1:
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = data[offset:]
            else:
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = \
                    data[extended_offset: extended_offset + extended_limit]
    else:
        result = data

    # little hack for XML proper serialization
    if request is not None and \
            request.META is not None and \
            'HTTP_ACCEPT' in request.META.keys() and \
            request.META['HTTP_ACCEPT'] == 'application/xml' and \
            settings.LAMB_PAGINATION_KEY_ITEMS in result.keys():

        result[settings.LAMB_PAGINATION_KEY_ITEMS] = {'item': result[settings.LAMB_PAGINATION_KEY_ITEMS]}
        tm.append_marker('vary based on header')

    return result


Sorter = Tuple[str, Callable]


def _get_instance_sorting_attribute_names(ins: object) -> List[str]:
    # TODO: add support for instance and model class params
    # TODO: cache results
    # discover sortable attributes
    sortable_attributes = set()

    # append columns
    sortable_attributes.update(set(ins.mapper.column_attrs.values()))

    # append hybrid attributes
    sortable_attributes.update(set([
        ormd for ormd in ins.all_orm_descriptors if type(ormd) == hybrid_property
    ]))

    result = []
    for ormd in sortable_attributes:
        if isinstance(ormd, Column):
            orm_attr_name = ormd.name
        elif isinstance(ormd, (ColumnProperty, QueryableAttribute)):
            orm_attr_name = ormd.key
        elif isinstance(ormd, hybrid_property):
            orm_attr_name = ormd.__name__
        else:
            logger.warning(f'Unsupported orm_descriptor type: {ormd, ormd.__class__}')
            raise exc.ServerError('Could not serialize data')
        result.append(orm_attr_name)

    return result


def _sorting_parse_sorter(raw_sorting_descriptor: str, model_inspection) -> Sorter:
    """ Parse single sorting descriptor """
    # check against regex and extract field and function
    full_regex = re.compile(r'^\w+{\w+}$')
    short_regex = re.compile(r'^\w+$')
    if full_regex.match(raw_sorting_descriptor) is not None:
        index = raw_sorting_descriptor.index('{')
        field = raw_sorting_descriptor[:index]
        sort_functor = raw_sorting_descriptor[index + 1:-1]
    elif short_regex.match(raw_sorting_descriptor) is not None:
        field = raw_sorting_descriptor
        sort_functor = 'desc'
    else:
        raise InvalidParamValueError('Invalid sorting descriptor format %s' % raw_sorting_descriptor,
                                     error_details={'key_path': 'sorting', 'descriptor': raw_sorting_descriptor})

    # check against meta data
    sortable_attributes = _get_instance_sorting_attribute_names(model_inspection)
    field = field.lower()
    if field not in sortable_attributes:
        raise InvalidParamValueError(
            'Invalid sorting_field value for descriptor %s. Not found in model' % raw_sorting_descriptor,
            error_details={'key_path': 'sorting', 'descriptor': raw_sorting_descriptor, 'field': field})

    sort_functor = sort_functor.lower()
    if sort_functor not in ['asc', 'desc']:
        raise InvalidParamValueError(
            'Invalid sorting_direction value for descriptor %s. Should be one [asc or desc]' % raw_sorting_descriptor,
            error_details={'key_path': 'sorting', 'descriptor': raw_sorting_descriptor})

    sort_functor = asc if sort_functor == 'asc' else desc

    return field, sort_functor


def _sorting_parse_descriptors(raw_sorting_descriptors: Optional[str], model_inspection) -> List[Sorter]:
    """ Parse list of sorting descriptors """
    # early return and check params
    if raw_sorting_descriptors is None:
        return []
    if not isinstance(raw_sorting_descriptors, str):
        logger.warning(f'Invalid sorting descriptors type received: {raw_sorting_descriptors}')
        raise InvalidParamTypeError('Invalid sorting descriptors type')
    raw_sorting_descriptors = unquote(raw_sorting_descriptors)  # dirty hack for invalid arg transfer
    raw_sorting_descriptors = raw_sorting_descriptors.lower()

    # parse data
    sorting_descriptors_list = raw_sorting_descriptors.split(',')
    sorting_descriptors_list = [sd for sd in sorting_descriptors_list if len(sd) > 0]
    result = []
    for sd in sorting_descriptors_list:
        result.append(_sorting_parse_sorter(sd, model_inspection))
    return result


def _sorting_apply_sorters(sorters: List[Sorter],
                           query: Query,
                           model_class: DeclarativeMeta,
                           check_duplicate: bool = True) -> Query:
    applied_sort_fields: List[str] = list()
    for (_sorting_field, _sorting_functor) in sorters:
        if _sorting_field in applied_sort_fields and check_duplicate:
            logger.debug(f'skip duplicate sorting field: {_sorting_field}')
            continue
        logger.debug(f'apply sorter: {_sorting_field, _sorting_functor}')
        query = query.order_by(_sorting_functor(getattr(model_class, _sorting_field)))
        applied_sort_fields.append(_sorting_field)
    return query


def response_sorted(
        query: Query,
        model_class: DeclarativeMeta,
        params: dict = None,
        default_sorting: str = None,
        **kwargs) -> Query:
    """ Apply order by sortings to sqlalchemy query instance from params dictionary

    :param query: SQLAlchemy query instance to be sorted
    :param model_class: Model class for columns introspection
    :param params: Dictionary that contains params of sorting
    :param default_sorting: Default sorting descriptors
    :param final_sorting: Final step sorting - if provided in kwargs it would be parsed as descriptor and applied
        to query. By default final step of sorting - is to sort via primary key of model class.
    :param start_sorting: Initial sorting step - if provided in kwargs it would be parsed as descriptor and applied
        to query before all other descriptors.
    """
    # check deprecation
    if 'params_dict' in kwargs and params is None:
        warnings.warn('response_sorted `params_dict` param is deprecated, use `params` instead', DeprecationWarning,
                      stacklevel=2)
        params = kwargs.pop('params_dict')

    # check params
    if not isinstance(params, dict):
        raise ServerError('Improperly configured sorting params dictionary')
    if not isinstance(model_class, DeclarativeMeta):
        raise ServerError('Improperly configured model class meta-data for sorting introspection')
    if not isinstance(query, Query):
        raise ServerError('Improperly configured query item for sorting')

    # prepare inspection and container
    model_inspection = inspect(model_class)

    # discover and apply start sorters
    all_sorters: List[Sorter] = []
    start_sorters = _sorting_parse_descriptors(
        raw_sorting_descriptors=kwargs.get('start_sorting', None),
        model_inspection=model_inspection
    )
    logger.debug(f'sorters parsed start_sorting: {start_sorters}')
    all_sorters.extend(start_sorters)

    # discover and apply client sorters
    client_sorters = _sorting_parse_descriptors(
        raw_sorting_descriptors=dpath_value(params, settings.LAMB_SORTING_KEY, str, default=default_sorting),
        model_inspection=model_inspection
    )
    logger.debug(f'sorters parsed client_sorters: {client_sorters}')
    all_sorters.extend(client_sorters)

    # discover and apply final sorters
    final_sorters = []
    if 'final_sorting' in kwargs.keys():
        # final_sorting exist - should parse and apply descriptors
        final_sorting_descriptors = kwargs['final_sorting']
        if final_sorting_descriptors is not None:
            final_sorters = _sorting_parse_descriptors(
                raw_sorting_descriptors=final_sorting_descriptors,
                model_inspection=model_inspection
            )
            logger.debug(f'sorters parsed final_sorters [explicit]: {final_sorters}')
    else:
        # if final sorting omitted - use primary key
        primary_key_columns = [c.name for c in model_inspection.primary_key]
        primary_key_descriptors = ','.join([f'{pk_column}{{desc}}' for pk_column in primary_key_columns])
        primary_key_sorters = _sorting_parse_descriptors(
            raw_sorting_descriptors=primary_key_descriptors,
            model_inspection=model_inspection
        )
        logger.debug(f'sorters parsed final_sorters [implicit pkey]: {final_sorters}')
        final_sorters = primary_key_sorters

    # apply sorters
    all_sorters.extend(final_sorters)
    query = _sorting_apply_sorters(
        sorters=all_sorters,
        query=query,
        model_class=model_class,
        check_duplicate=True
    )

    return query


def response_filtered(
        query: Query,
        filters: List['lamb.utils.filters.Filter'],
        request: LambRequest = None,
        params: Dict = None) -> Query:
    # check params override
    if request is not None and params is None:
        params = request.GET

    # check params
    from lamb.utils.filters import Filter
    if not isinstance(query, Query):
        logger.warning('Invalid query data type: %s' % query)
        raise ServerError('Improperly configured query item for filtering')
    
    for f in filters:
        if not isinstance(f, Filter):
            logger.warning('Invalid filters item data type: %s' % f)
            raise ServerError('Improperly configured filters for filtering')

    # apply filters
    for f in filters:
        query = f.apply_to_query(query=query, params=params)

    return query


# compacting
def compact(obj: Union[list, dict]) -> Union[list, dict]:
    """ Compact version of container """
    if isinstance(obj, list):
        return [o for o in obj if o is not None]
    elif isinstance(obj, dict):
        return {k: v for k, v in obj.items() if v is not None}
    else:
        return obj


def compact_dict(dct: dict) -> dict:
    """ Compact dict by removing keys with None value """
    warnings.warn('compact_dict deprecated, use compact instead', DeprecationWarning, stacklevel=2)
    return compact(dct)


def compact_list(lst: list) -> list:
    """ Compact list by removing None values """
    warnings.warn('compact_list deprecated, use compact instead', DeprecationWarning, stacklevel=2)
    return compact(lst)


# content/response encoding
CONTENT_ENCODING_JSON = 'application/json'
CONTENT_ENCODING_XML = 'application/xml'
CONTENT_ENCODING_MULTIPART = 'multipart/form-data'


def _get_encoding_for_header(request: HttpRequest, header: str) -> str:
    """" Extract header value from request and interpret it as encoding value

    :raises InvalidParamTypeError: In case header value is not of type string
    """
    # check param types
    if not isinstance(request, HttpRequest):
        raise InvalidParamTypeError('Invalid request instance datatype to determine encoding')
    if not isinstance(header, str):
        raise InvalidParamTypeError('Invalid header datatype to determine encoding')

    # extract header
    header = header.upper()
    header_value = request.META.get(header, 'application/json')
    if not isinstance(header_value, str):
        raise InvalidParamTypeError('Invalid datatype of header value to determine encoding')

    header_value = header_value.lower()
    prefix_mapping = {
        'application/json': CONTENT_ENCODING_JSON,
        'application/xml': CONTENT_ENCODING_XML,
        'text/xml': CONTENT_ENCODING_XML,
        'multipart/form-data': CONTENT_ENCODING_MULTIPART,
    }
    result = header_value
    for key, value in prefix_mapping.items():
        if header_value.startswith(key):
            result = value
            break

    return result


def get_request_body_encoding(request: HttpRequest) -> str:
    """ Extract request body encoding operating over Content-Type HTTP header """
    return _get_encoding_for_header(request, 'CONTENT_TYPE')


def get_request_accept_encoding(request: HttpRequest) -> str:
    """ Extract request accept encoding operating over Http-Accept HTTP header """
    return _get_encoding_for_header(request, 'HTTP_ACCEPT')


# datetime
def datetime_end(value: Union[date, datetime]) -> datetime:
    if not isinstance(value, (date, datetime)):
        raise InvalidParamTypeError('Invalid data type for date/datetime convert')

    return datetime(
        year=value.year,
        month=value.month,
        day=value.day,
        hour=23,
        minute=59,
        second=59,
        microsecond=999,
        tzinfo=getattr(value, 'tzinfo', None)
    )


def datetime_begin(value: Union[date, datetime]) -> datetime:
    if not isinstance(value, (date, datetime)):
        raise InvalidParamTypeError('Invalid data type for date/datetime convert')

    return datetime(
        year=value.year,
        month=value.month,
        day=value.day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=getattr(value, 'tzinfo', None)
    )


# other
def import_by_name(name: str):
    # try to import as module
    def _import_module(_name) -> Optional[types.ModuleType]:
        try:
            return importlib.import_module(_name)
        except ImportError:
            return None

    res = _import_module(name)
    if res is None:
        module, _, func_or_class = name.rpartition('.')
        mod = _import_module(module)
        try:
            res = getattr(mod, func_or_class)
        except AttributeError as e:
            raise ImportError(f'Could not load {name}') from e

    return res


def import_class_by_name(name):
    warnings.warn('import_class_by_name deprecated, use lamb.utils.transformers.import_by_name instead', DeprecationWarning,
                  stacklevel=2)
    return import_by_name(name=name)


def inject_app_defaults(application: str):
    """Inject an application's default settings"""
    try:
        __import__('%s.settings' % application)
        import sys

        # Import our defaults, project defaults, and project settings
        _app_settings = sys.modules['%s.settings' % application]
        _def_settings = sys.modules['django.conf.global_settings']
        _settings = sys.modules['django.conf'].settings

        # Add the values from the application.settings module
        for _k in dir(_app_settings):
            if _k.isupper():
                # Add the value to the default settings module
                setattr(_def_settings, _k, getattr(_app_settings, _k))

                # Add the value to the settings, if not already present
                if not hasattr(_settings, _k):
                    setattr(_settings, _k, getattr(_app_settings, _k))
    except ImportError:
        # Silently skip failing settings modules
        pass


def string_to_uuid(value: str = '', key: Optional[str] = None) -> uuid.UUID:
    """ Convert string into UUID value

    :param value: Value to convert in uuid object
    :param key: Optional key value to include in exception details info

    :raises InvalidParamValueError: If converting process failed
    """
    from lamb.utils.transformers import transform_uuid
    warnings.warn('string_to_uuid deprecated, use lamb.utils.transformers.transform_uuid instead', DeprecationWarning,
                  stacklevel=2)
    return transform_uuid(value, key)


def url_append_components(baseurl: str = '', components: List[str] =list()) -> str:
    """ Append path components to url """
    components = [str(c) for c in components]
    split = urlsplit(baseurl)
    scheme, netloc, path, query, fragment = (split[:])
    if len(path) > 0:
        components.insert(0, path)
    path = '/'.join(c.strip('/') for c in components)
    result = urlunsplit((scheme, netloc, path, query, fragment))
    return result


def clear_white_space(value: Optional[str]) -> Optional[str]:
    """ Clear whitespaces from string: from begining, from ending and repeat in body

    :raises InvalidParamTypeError: In case of value is not string
    """
    if value is None:
        return value
    if not isinstance(value, str):
        raise InvalidParamTypeError('Invalid param type, string expected')
    return ' '.join(value.split())


def random_string(length: int = 10, char_set: str = string.ascii_letters + string.digits) -> str:
    """ Generate random string

    :param length: Length of string to generate, by default 10
    :param char_set: Character set as string to be used as source for random, by default alphanumeric
    """
    result = ''
    for _ in range(length):
        result += random.choice(char_set)
    return result


class DeprecationClassHelper(object):
    def __init__(self, new_target):
        self.new_target = new_target

    def _warn(self):
        warnings.warn(f'Class is deprecated, use {self.new_target} instead', DeprecationWarning, stacklevel=3)

    def __call__(self, *args, **kwargs):
        self._warn()
        return self.new_target(*args, **kwargs)

    def __getattr__(self, attr):
        self._warn()
        return getattr(self.new_target, attr)


def check_device_info_min_versions(request: LambRequest, min_versions: List[Tuple[str, int]]):
    # TODO: migrate to support independent device_info object and not only request
    """ Minimum app version checker

    If request object have info about platform and app build will check compatibility of versions:
    - by default for requests without device info and not specified platforms - skip without exception
    - raise `UpdateRequiredError` if version detected and below minimal requirements
    """
    if request is None:
        return
    if request.lamb_device_info.app_build is None:
        return
    if request.lamb_device_info.device_platform is None:
        return

    for min_v in min_versions:
        try:
            _platform = min_v[0]
            _min_app_build = min_v[1]
            if request.lamb_device_info.device_platform == _platform and _min_app_build > request.lamb_device_info.app_build:
                raise UpdateRequiredError
        except UpdateRequiredError:
            raise
        except Exception as e:
            logger.warning('Skip min version checking for %s cause of invalid structure, error: %s' % (min_v, e))
            continue


def masked_dict(dct: Dict[Any, Any], *masking_keys) -> Dict[Any, Any]:
    return {k: v if k not in masking_keys else '*****' for k, v in dct.items()}


_timed_lru_cache_functions: Dict[Callable, Callable] = {}


def timed_lru_cache(**timedelta_kwargs):
    def _wrapper(func):
        update_delta = timedelta(**timedelta_kwargs)
        next_update = datetime.utcnow() + update_delta
        func_full_name = f'{sys.modules[func.__module__].__name__}.{func.__name__}'
        logger.debug(f'timed_lru_cache initial update calculated: {func_full_name} -> {next_update}')
        # Apply @lru_cache to func with no cache size limit
        func_lru_cached = functools.lru_cache(None)(func)

        _timed_lru_cache_functions[func] = func_lru_cached
        logger.debug(f'time cached functions: {_timed_lru_cache_functions}')

        @functools.wraps(func_lru_cached)
        def _wrapped(*args, **kwargs):
            nonlocal next_update
            now = datetime.utcnow()
            if now >= next_update:
                func_lru_cached.cache_clear()
                next_update = now + update_delta
                logger.debug(f'timed_lru_cache next update calculated: {func_full_name} -> {next_update}')
            return func_lru_cached(*args, **kwargs)

        return _wrapped

    return _wrapper


def timed_lru_cache_clear():
    for func, wrapped_func in _timed_lru_cache_functions.items():
        wrapped_func.cache_clear()
        logger.warning(f'time_lru_cache cleared for: {func} -> {wrapped_func}')


def list_chunks(lst: list, n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# async downloads
@enum.unique
class AsyncFallStrategy(str, enum.Enum):
    RAISING = 'RAISING'
    NONE = 'NONE'
    EXCEPTION = 'EXCEPTION'


def _handle_async_fall(e: Exception, fall_strategy: AsyncFallStrategy):
    if fall_strategy == AsyncFallStrategy.RAISING:
        raise e
        # raise ExternalServiceError(f'Could not download resource, network error: {url}') from e
    elif fall_strategy == AsyncFallStrategy.NONE:
        return None
    elif fall_strategy == AsyncFallStrategy.EXCEPTION:
        return e
    else:
        logger.warning(f'Invalid strategy received: {fall_strategy}')
        raise ServerError('Invalid async fall strategy mode')


@sync_to_async
def _async_download_url(url: Optional[str],
                        timeout,
                        fall_strategy: AsyncFallStrategy,
                        headers: Optional[Dict[str, Any]] = None
                        ) -> Optional[bytes]:
    logger.debug(f'downloading resource from url: {url}, timeout={timeout}, headers={headers}')
    if url is None:
        return None
    else:
        try:
            headers = headers or {}
            res = requests.get(url, timeout=timeout, headers=headers)
            if res.status_code != 200:
                raise ExternalServiceError(f'Could not download resource, invalid status: {url}')
            return res.content
        except Exception as e:
            return _handle_async_fall(e, fall_strategy)
            # if fall_strategy == AsyncFallStrategy.RAISING:
            #     raise
            # elif fall_strategy == AsyncFallStrategy.NONE:
            #     return None
            # elif fall_strategy == AsyncFallStrategy.EXCEPTION:
            #     return e
            # else:
            #     logger.warning(f'Invalid strategy received: {fall_strategy}')
            #     raise ServerError('Invalid async fall strategy mode')


async def _async_download_resources(urls: List[Optional[str]],
                                    timeout: int,
                                    fall_strategy: AsyncFallStrategy,
                                    headers: Optional[Dict[str, Any]] = None
                                    ) -> List[Optional[bytes]]:
    tasks = []
    for url in urls:
        tasks.append(_async_download_url(url=url, timeout=timeout, headers=headers, fall_strategy=fall_strategy))
    result = await asyncio.gather(*tasks)

    return result


def async_download_resources(urls: List[Optional[str]],
                             timeout=30,
                             headers: Optional[Dict[str, Any]] = None,
                             fall_strategy: AsyncFallStrategy = AsyncFallStrategy.RAISING
                             ) -> List[Optional[bytes]]:
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _async_download_resources(urls=urls, timeout=timeout, headers=headers, fall_strategy=fall_strategy)
        )
    finally:
        loop.close()
    return result


def async_download_images(urls: List[Optional[str]],
                          timeout=30,
                          headers: Optional[Dict[str, Any]] = None,
                          fall_strategy: AsyncFallStrategy = AsyncFallStrategy.RAISING
                          ) -> List[Optional[PILImage.Image]]:
    result = async_download_resources(urls=urls, timeout=timeout, headers=headers, fall_strategy=fall_strategy)
    buffer = []
    for index, res in enumerate(result):
        try:
            if res is None:
                buffer.append(None)
                continue
            buffer.append(PILImage.open(io.BytesIO(res)))
        except Exception as e:
            buffer.append(_handle_async_fall(e, fall_strategy))
    return buffer


def image_convert_to_rgb(image: PILImage.Image) -> PILImage.Image:
    if image.mode == 'RGBA':
        image.load()
        background = PILImage.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        return background
    else:
        return image.convert('RGB')


def file_is_svg(file: Union[str, BinaryIO]) -> bool:

    try:
        tag = next(cElementTree.iterparse(file, ('start',)))[1].tag
    except cElementTree.ParseError:
        return False

    return tag == '{http://www.w3.org/2000/svg}svg'
