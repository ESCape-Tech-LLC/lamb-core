#-*- coding: utf-8 -*-
import enum

from lamb.rest.middleware import logger

__author__ = 'KoNEW'


import random
import string
import json
import dpath
import uuid
import warnings
import re

from urllib.parse import urlsplit, urlunsplit
from collections import OrderedDict
from sqlalchemy import asc, desc, func, or_, any_
from sqlalchemy.orm import Query
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.inspection import inspect
from django.http import HttpRequest
from django.conf import settings

from lamb.rest.exceptions import InvalidBodyStructureError, InvalidParamTypeError, InvalidParamValueError, ServerError


__all__ = [
    'LambRequest', 'parse_body_as_json',  'dpath_value', 'string_to_uuid', 'validated_interval',
    'random_string','url_append_components', 'clear_white_space',
    'compact_dict', 'compact_list', 'compact',
    'paginated', 'response_paginated', 'response_sorted',

    'get_request_body_encoding', 'get_request_accept_encoding',
    'CONTENT_ENCODING_XML', 'CONTENT_ENCODING_JSON'
]


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
def parse_body_as_json(request):
    """  Parse request object to dictionary as JSON

    :param request: Request object
    :type request: django.http.HttpRequest
    :return:  Body parsed as JSON object
    :rtype: dict
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


def dpath_value(dict_object=None, key_path=None, req_type=None, allow_none=False, **kwargs):
    """ Search for object in dictionary
    :param dict_object: Dictionary to find data
    :type dict_object: dict
    :param key_path: Query string, separated via /
    :type key_path: basestring
    :param req_type: Type of argument that expected
    :type req_type: Class
    :param allow_none: Return None withour exception if leaf exist and equal to None
    :type allow_none: bool
    :return: Extracted value
    :raises InvalidBodyStructureError: In case of non dict as first variable
    :raises InvalidParamTypeError: In case of extracted type impossible to convert in req_type
    :raises ServerError: In case of invalid key_path type
    """
    def type_convert(req_type, value):
        if req_type is None:
            return value
        if isinstance(value, req_type):
            return value
        try:
            value = req_type(value)
            return value
        except (ValueError, TypeError) as e:
            raise InvalidParamTypeError('Invalid data type for param %s' % key_path, error_details={'key_path': key_path}) from e
    try:
        items = dpath.util.values(dict_object, key_path)
        result = items[0]

        if req_type is None:
            return result

        if result is None:
            if allow_none:
                return None
            else:
                raise InvalidParamTypeError('Invalid data type for param %s' % key_path, error_details={'key_path': key_path})

        result = type_convert(req_type, result)
        return result
    except IndexError as e:
        if 'default' in kwargs.keys():
            return kwargs['default']
        else:
            raise InvalidBodyStructureError('Could not extract param for key_path %s from provided dict data' % key_path, error_details={'key_path': key_path}) from e
    except AttributeError as e:
        raise ServerError('Invalid key_path type for querying in dict', error_details={'key_path': key_path}) from e


def validated_interval(value, bottom, top, key=None, allow_none=False):
    if value is None and allow_none == True:
        return value

    try:
        if value < bottom or value > top:
            raise InvalidParamValueError('Invalid param %s value or type, should be between %s and %s' % (key, bottom, top), error_details=key)
        return value
    except InvalidParamValueError as e:
        raise e
    except:
        raise InvalidParamTypeError('Invalid param type for %s' % key, error_details=key)


# reponse utilities
def random_string(length=10, char_set = string.ascii_letters + string.digits):
    result = ''
    for _ in range(length):
        result += random.choice(char_set)
    return result


def paginated(data, request):
    """
    :param data: Instance of list or query to be paginated
    :type data: (list | Query)
    :param request: Http request
    :type request: pynm.utils.LambRequest
    """
    warnings.warn('paginated method is deprecated, use response_paginated version', DeprecationWarning)
    return response_paginated(data, request)
    # # parse and check offset
    # offset = dpath_value(request.GET, settings.LAMB_PAGINATION_KEY_OFFSET, int, default=0)
    # if offset < 0:
    #     raise InvalidParamValueError('Invalid offset value for pagination',
    #                                  error_details=settings.LAMB_PAGINATION_KEY_OFFSET)
    #
    # # parse and check limit
    # limit = dpath_value(request.GET, settings.LAMB_PAGINATION_KEY_LIMIT, int,
    #                     default=settings.LAMB_PAGINATION_LIMIT_DEFAULT)
    # if limit < -1:
    #     raise InvalidParamValueError('Invalid limit value for pagination',
    #                                  error_details=settings.LAMB_PAGINATION_KEY_LIMIT)
    # if limit > settings.LAMB_PAGINATION_LIMIT_MAX:
    #     raise InvalidParamValueError('Invalid limit value for pagination - exceed max available',
    #                                  error_details=settings.LAMB_PAGINATION_KEY_LIMIT)
    #
    # # prepare result container
    # result = OrderedDict()
    # result[settings.LAMB_PAGINATION_KEY_OFFSET] = offset
    # result[settings.LAMB_PAGINATION_KEY_LIMIT] = limit
    #
    # if isinstance(data, Query):
    #     result[settings.LAMB_PAGINATION_KEY_TOTAL] = data.count()
    #     result[settings.LAMB_PAGINATION_KEY_ITEMS] = data.offset(offset).limit(limit).all()
    # elif isinstance(data, list):
    #     result[settings.LAMB_PAGINATION_KEY_TOTAL] = len(data)
    #     result[settings.LAMB_PAGINATION_KEY_ITEMS] = data[ offset : offset+limit ]
    # else:
    #     result = data
    #
    # # little hack for XML proper serialization
    # # TODO: migrate to determine in middleware
    # if request is not None and \
    #         request.META is not None and \
    #         'HTTP_ACCEPT' in request.META.keys() and \
    #         request.META['HTTP_ACCEPT'] == 'application/xml' and \
    #         settings.LAMB_PAGINATION_KEY_ITEMS in result.keys():
    #
    #     result[settings.LAMB_PAGINATION_KEY_ITEMS] = {'item': result[settings.LAMB_PAGINATION_KEY_ITEMS]}
    #
    # return result


def response_paginated(data, request):
    """
    :param data: Instance of list or query to be paginated
    :type data: (list | Query)
    :param request: Http request
    :type request: pynm.utils.LambRequest
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

    # prepare result container
    result = OrderedDict()
    result[settings.LAMB_PAGINATION_KEY_OFFSET] = offset
    result[settings.LAMB_PAGINATION_KEY_LIMIT] = limit

    if isinstance(data, Query):
        result[settings.LAMB_PAGINATION_KEY_TOTAL] = data.count()
        result[settings.LAMB_PAGINATION_KEY_ITEMS] = data.offset(offset).limit(limit).all()
    elif isinstance(data, list):
        result[settings.LAMB_PAGINATION_KEY_TOTAL] = len(data)
        result[settings.LAMB_PAGINATION_KEY_ITEMS] = data[ offset : offset+limit ]
    else:
        result = data

    # little hack for XML proper serialization
    # TODO: migrate to determine in middleware
    if request is not None and \
            request.META is not None and \
            'HTTP_ACCEPT' in request.META.keys() and \
            request.META['HTTP_ACCEPT'] == 'application/xml' and \
            settings.LAMB_PAGINATION_KEY_ITEMS in result.keys():

        result[settings.LAMB_PAGINATION_KEY_ITEMS] = {'item': result[settings.LAMB_PAGINATION_KEY_ITEMS]}

    return result


def response_sorted(query, model_class, params_dict, default_sorting=None):
    """
    :param query: SQLAlchemy session query instance to be sorted
    :type query: sqlalchemy.orm.Query
    :param model_class: Model class for columns introspection
    :type model_class: DeclarativeMeta
    :param params_dict: Dictionary that contains params of sorting
    :type params_dict: dict
    :param default_sorting: Default sorting descriptions
    :type default_sorting: str | None
    :return: Modified query item
    :rtype: sqlalchemy.orm.Query
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

    # finally sort via primary key fields to guarantee order
    primary_key_columns = [c.name for c in model_inspection.primary_key]
    for pk_column in primary_key_columns:
        if pk_column in applied_fields:
            continue
        query = query.order_by(desc(getattr(model_class, pk_column)))

    return query


def string_to_uuid(value='', key=None):
    """ Utility function to convert string into user id

    :param value: Value to convert in uuid object
    :return: Converted uuid object
    :rtype: uuid.UUID
    :raises InvalidParamValueError: If converting process failed
    """
    try:
        return uuid.UUID(value)
    except ValueError:
        raise InvalidParamValueError('Invalid value for uuid field', error_details=key)


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


def clear_white_space(value):
    """ Clear whitespaces from string: from begining, from ending and repeat in body
    :param value: String to clear
    :type value: str
    :rtype: str
    """
    if value is None:
        return value
    if not isinstance(value, str):
        raise InvalidParamTypeError('Invalid param type, string expected')
    return ' '.join(value.split())


# other
def compact(obj):
    """
    :type obj: list | dict
    :return: list | dict
    """
    if isinstance(obj, list):
        return [o for o in obj if o is not None]
    elif isinstance(obj, dict):
        return {k:v for k, v in obj.items() if v is not None}
    else:
        return obj


def compact_dict(dct):
    """
    :type dct: dict
    :rtype: dict
    """
    warnings.warn('compact_dict depreacted, use compact instead', DeprecationWarning)
    return compact(dct)


def compact_list(lst):
    """ Remove None items from list
    :type lst: list
    :rtype: list
    """
    warnings.warn('compact_list depreacted, use compact instead', DeprecationWarning)
    return compact(lst)


# content/response encoding
CONTENT_ENCODING_JSON = 'application/json'
CONTENT_ENCODING_XML = 'application/xml'


def _get_request_encdoing(request, header):
    """"
    :type request: lamb.utils.LambRequest
    :type header: str
    :rtype: str
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
    if header_value.startswith('application/json'):
        result = CONTENT_ENCODING_JSON
    elif header_value.startswith('application/xml') or header_value.startswith('text/xml'):
        result = CONTENT_ENCODING_XML
    else:
        result = header_value

    return result


def get_request_body_encoding(request):
    """"
    :type request: lamb.utils.LambRequest
    :rtype: ContentEncoding
    """
    return _get_request_encdoing(request, 'CONTENT_TYPE')


def get_request_accept_encoding(request):
    """"
    :type request: lamb.utils.LambRequest
    :rtype: ContentEncoding
    """
    return _get_request_encdoing(request, 'HTTP_ACCEPT')