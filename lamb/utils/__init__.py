#-*- coding: utf-8 -*-
__author__ = 'KoNEW'


import random
import string
import json
import uuid
import warnings
import logging
import re

from typing import List, Union, TypeVar, Optional
from urllib.parse import urlsplit, urlunsplit, unquote
from collections import OrderedDict
from sqlalchemy import asc, desc, func, or_, any_
from sqlalchemy.orm import Query
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.inspection import inspect
from django.http import HttpRequest
from django.conf import settings

from lamb.exc import InvalidBodyStructureError, InvalidParamTypeError, InvalidParamValueError, ServerError
from .dpath import dpath_value

__all__ = [
    'LambRequest', 'parse_body_as_json',  'dpath_value', 'string_to_uuid', 'validated_interval',
    'random_string','url_append_components', 'clear_white_space',
    'compact_dict', 'compact_list', 'compact',
    'paginated', 'response_paginated', 'response_sorted', 'response_filtered',

    'get_request_body_encoding', 'get_request_accept_encoding',
    'CONTENT_ENCODING_XML', 'CONTENT_ENCODING_JSON', 'CONTENT_ENCODING_MULTIPART',
    'dpath_value',

    'import_class_by_name'
]


logger = logging.getLogger(__name__)


class LambRequest(HttpRequest):
    """ Class used only for proper type hinting in pycharm, not guarantee that properties will exist
    :type lamb_db_session: sqlalchemy.orm.Session | None
    :type lamb_execution_meter: lamb.execution_time.ExecutionTimeMeter | None
    :type lamb_device_info: lamb.service.device_info.model.DeviceInfo
    """
    def __init__(self):
        super(LambRequest, self).__init__()
        self.lamb_db_session = None
        self.lamb_execution_meter = None
        self.lamb_device_info = None


# parsing
def parse_body_as_json(request: HttpRequest) -> dict:
    """  Parse request object to dictionary as JSON

    :param request: Request object

    :return:  Body parsed as JSON object

    :raises InvalidBodyStructureError: In case of parsing failed or parsed object is not dictionary
    """
    try:
        body = request.body
    except:
        raise ServerError('Invalid request object')

    try:
        data = json.loads(body)
        if not isinstance(data, dict):
            raise InvalidBodyStructureError('JSON body of request should be represented in a form of dictionary')
        return data
    except ValueError as e:
        raise InvalidBodyStructureError('Could not parse body as JSON object')


VT = TypeVar('VT')


def validated_interval(value: Optional[VT],
                       bottom: VT,
                       top: VT,
                       key: str = None,
                       allow_none: bool = False) -> Optional[VT]:
    """ Value within interval validator

    :param value: Value to be checked
    :param bottom: Interval bottom limit
    :param top: Interval top limit
    :param key: Optional key to include in exception description as details
    :param allow_none: Flag to make None value valid returnoing None

    :raises InvalidParamValueError: In case of value out of interval
    :raises InvalidParamTypeError: In case of any other exception
    """
    if value is None and allow_none == True:
        return value

    try:
        if value < bottom or value > top:
            raise InvalidParamValueError('Invalid param %s value or type, should be between %s and %s' % (key, bottom, top), error_details=key)
        return value
    except InvalidParamValueError:
        raise
    except:
        raise InvalidParamTypeError('Invalid param type for %s' % key, error_details=key)


# reponse utilities
PV = TypeVar('PV', list, Query)

def paginated(data: PV, request: LambRequest) -> dict:
    """ Deprected version of pagination utility

    :param data: Instance of list or query to be paginated
    :param request: Http request
    """
    warnings.warn('paginated method is deprecated, use response_paginated version', DeprecationWarning, stacklevel=2)
    return response_paginated(data, request)


def response_paginated(data: PV, request: LambRequest, add_extended_query: bool = False) -> dict:
    """ Pagination utility

    Will search for limit/offset params in `request.GET` object and apply it to data, returning
    dictionary that includes info about real offset, limit, total_count, items.

    :param data: Instance of list or query to be paginated
    :param request: Http request
    :param add_extended_query: Flag to add to result extended version of data slice
        (including one more item from begin and and of slice)
    """
    # parse and check offset
    offset = dpath_value(request.GET, settings.LAMB_PAGINATION_KEY_OFFSET, int, default=0)
    if offset < 0:
        raise InvalidParamValueError('Invalid offset value for pagination',
                                     error_details=settings.LAMB_PAGINATION_KEY_OFFSET)

    # parse and check limit
    limit = dpath_value(request.GET, settings.LAMB_PAGINATION_KEY_LIMIT, int,
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
        # TODO: Add dynamic count function choose based on any join presented in query
        def get_count(q):
            # TODO: modify query - returns invalid count in case of join with one-to-many objects
            count_q = q.statement.with_only_columns([func.count()]).order_by(None)
            count = q.session.execute(count_q).scalar()
            return count

        # result[settings.LAMB_PAGINATION_KEY_TOTAL] = get_count(data)
        result[settings.LAMB_PAGINATION_KEY_TOTAL] = data.count()
        if limit == -1:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data.offset(offset).all()
        else:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data.offset(offset).limit(limit).all()

        if add_extended_query:
            if extended_limit == -1:
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = data.offset(extended_offset).all()
            else:
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = data.offset(extended_offset).limit(extended_limit).all()
    elif isinstance(data, list):
        result[settings.LAMB_PAGINATION_KEY_TOTAL] = len(data)
        if limit == -1:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data[ offset : ]
        else:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data[offset: offset + limit]

        if add_extended_query:
            if extended_limit == -1:
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = data[ offset : ]
            else:
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = data[ extended_offset : extended_offset + extended_limit]
    else:
        result = data

    # little hack for XML proper serialization
    if request is not None and \
            request.META is not None and \
            'HTTP_ACCEPT' in request.META.keys() and \
            request.META['HTTP_ACCEPT'] == 'application/xml' and \
            settings.LAMB_PAGINATION_KEY_ITEMS in result.keys():

        result[settings.LAMB_PAGINATION_KEY_ITEMS] = {'item': result[settings.LAMB_PAGINATION_KEY_ITEMS]}

    return result


def response_sorted(query: Query, model_class: DeclarativeMeta, params_dict: dict,
                    default_sorting: str = None, **kwargs) -> Query:
    """ Apply order by sortings to sqlalchemy query instance from params dictionary

    :param query: SQLAlchemy query instance to be sorted
    :param model_class: Model class for columns introspection
    :param params_dict: Dictionary that contains params of sorting
    :param default_sorting: Default sorting descriptors
    :param final_sorting: Final step sorting - if provided in kwargs it would be parsed as descriptor andd applied
        to query. By default final step of sorting - is to sort via primary key of model class.
    """
    def extract_sorting_params(_sorting_description, _model_inspection):
        """
        :param _sorting_description: Raw sorting description
        :type _sorting_description: str
        :param _model_inspection: Inspection of model class
        :type _model_inspection: sqlalchemy.orm.mapper.Mapper
        :return: Tuple of atttibute name and sorting function (by default sorting function is desc)
        :rtype: (str, callable)
        """
        # check against regex and extract field and function
        full_regex = re.compile(r'^\w+{\w+}$')
        short_regex = re.compile(r'^\w+$')
        if full_regex.match(_sorting_description) is not None:
            index = _sorting_description.index('{')
            _field = _sorting_description[:index]
            _function = _sorting_description[index+1:-1]
        elif short_regex.match(_sorting_description) is not None:
            _field = _sorting_description
            _function = 'desc'
        else:
            raise InvalidParamValueError('Invalid sorting descriptor format %s' % _sorting_description,
                                         error_details={'key_path': 'sorting', 'descriptor': _sorting_description})

        # check against meta data
        _field = _field.lower()
        if _field not in [c.name for c in _model_inspection.columns]:
            raise InvalidParamValueError(
                'Invalid sorting_field value for descriptor %s. Not found in model' % _sorting_description,
                error_details={'key_path': 'sorting', 'descriptor': _sorting_description, 'field': _field})

        _function = _function.lower()
        if _function not in ['asc', 'desc']:
            raise InvalidParamValueError(
                'Invalid sorting_direction value for descriptor %s. Should be one of [asc, desc]' % _sorting_description,
                error_details={'key_path': 'sorting', 'descriptor': _sorting_description})

        _function = asc if _function == 'asc' else desc

        return _field, _function

    # check params
    if default_sorting is not None and not isinstance(default_sorting, str):
        raise ServerError('Improperly configured default_sorting descriptors')
    if not isinstance(params_dict, dict):
        raise ServerError('Improperly configured sorting params dictionary')
    if not isinstance(model_class, DeclarativeMeta):
        raise ServerError('Improperly configured model class meta-data for sorting introspection')
    if not isinstance(query, Query):
        raise ServerError('Improperly configured query item for sorting')

    # prepare model meta-data inspection
    model_inspection = inspect(model_class)

    # extract sorting descriptions
    sorting_descriptions = dpath_value(params_dict, settings.LAMB_SORTING_KEY, str, default=default_sorting)
    if sorting_descriptions is not None:
        sorting_descriptions = unquote(sorting_descriptions)  # dirty hack for invalid arg transfer

    if sorting_descriptions is None:
        sorting_descriptions = ''
    else:
        sorting_descriptions = sorting_descriptions.lower()

    # parse sorting descriptions
    applied_fields = list()
    sorting_descriptions = sorting_descriptions.split(',')
    sorting_descriptions = [s for s in sorting_descriptions if len(s) > 0]
    for sorting_description in sorting_descriptions:
        sorting_field, sorting_function = extract_sorting_params(sorting_description, model_inspection)
        applied_fields.append(sorting_field)
        query = query.order_by(sorting_function(getattr(model_class, sorting_field)))

    # discover final sorting attribute
    if 'final_sorting' in kwargs.keys():
        # final_sorting exist - should parse and apply descritors
        f_sorting_descriptors = kwargs['final_sorting']
        if not isinstance(f_sorting_descriptors, str):
            raise ServerError('Improperly configured final sorting descriptor')
        f_sorting_descriptors = f_sorting_descriptors.split(',')
        f_sorting_descriptors = [f for f in f_sorting_descriptors if len(f_sorting_descriptors) > 0]
        for f_descriptor in f_sorting_descriptors:
            _sorting_field, _sorting_function = extract_sorting_params(f_descriptor, model_inspection)
            applied_fields.append(_sorting_field)
            query = query.order_by(_sorting_function(getattr(model_class, _sorting_field)))
    else:
        # if final sorting omitted - use primary key
        primary_key_columns = [c.name for c in model_inspection.primary_key]
        for pk_column in primary_key_columns:
            if pk_column in applied_fields:
                continue
            query = query.order_by(desc(getattr(model_class, pk_column)))

    return query


def response_filtered(query: Query, filters: List['lamb.utils.Filter'], request: LambRequest = None) -> Query:
    # check params
    from lamb.utils.filters import Filter
    if not isinstance(query, Query):
        logger.warning('Invalid query data type: %s' % query)
        raise ServerError('Improperly configured query item for filterong')
    
    for f in filters:
        if not isinstance(f, Filter):
            logger.warning('Invalid filters item data type: %s' % f)
            raise ServerError('Improperly configured filters for filtering')

    # apply filters
    for f in filters:
        query = f.apply_to_query(query=query, request=request)

    return query



# compacting
def compact(obj: Union[list, dict]) -> Union[list, dict]:
    """ Compact version of container """
    if isinstance(obj, list):
        return [o for o in obj if o is not None]
    elif isinstance(obj, dict):
        return {k:v for k, v in obj.items() if v is not None}
    else:
        return obj


def compact_dict(dct: dict) -> dict:
    """ Compact dict by removing keys with None value """
    warnings.warn('compact_dict depreacted, use compact instead', DeprecationWarning)
    return compact(dct)


def compact_list(lst: list) -> list:
    """ Compact list by removing None values """
    warnings.warn('compact_list depreacted, use compact instead', DeprecationWarning)
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


# other
def import_class_by_name(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def string_to_uuid(value: str = '', key: Optional[str] = None) -> uuid.UUID:
    """ Convert string into UUID value

    :param value: Value to convert in uuid object
    :param key: Optional key value to include in exception details info

    :raises InvalidParamValueError: If converting process failed
    """
    from lamb.utils.transformers import transform_uuid
    warnings.warn('string_to_uuid depreacted, use lamb.utils.transformers.transform_uuid instead', DeprecationWarning)
    return transform_uuid(value, key)


def url_append_components(baseurl='', components=list()):
    """
    :type baseurl: basestring
    :type components: list[basestring]
    :rtype: basestring
    """
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
