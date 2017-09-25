__author__ = 'KoNEW'
#-*- coding: utf-8 -*-

import random
import string
import json
import dpath
import uuid

from urllib.parse import urlsplit, urlunsplit
from collections import OrderedDict

from sqlalchemy.orm import Query

from django.http import HttpRequest
from django.conf import settings

from lamb.rest.exceptions import InvalidBodyStructureError, InvalidParamTypeError, InvalidParamValueError, ServerError

__all__ = [
    'LambRequest', 'parse_body_as_json', 'dpath_value', 'validated_interval',
    'random_string', 'paginated', 'string_to_uuid', 'url_append_components'
]

class LambRequest(HttpRequest):
    """ Class used only for proper type hinting in pycharm, not guarantee that properties will exist
    :type lamb_db_session: sqlalchemy.orm.Session | None
    :type lamb_execution_meter: lamb.execution_time.ExecutionTimeMeter | None
    """
    def __init__(self):
        super(LambRequest, self).__init__()
        self.lamb_db_session = None
        self.lamb_execution_meter = None


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
    :param kwargs: Additional params, only 'default' acceptable that will be return in case of not found key path
    :type kwargs: dict
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
    offset = dpath_value(request.GET, 'offset', int, default=0)
    if offset < 0:
        raise InvalidParamValueError('Invalid offset value for pagination', error_details='offset')
    limit = dpath_value(request.GET, 'limit', int, default=settings.LAMB_PAGINATION_WINDOW)
    if limit < -1:
        raise InvalidParamValueError('Invalid limit value for pagination', error_details='limit')
    if limit > settings.LAMB_PAGINATION_WINDOW:
        limit = settings.LAMB_PAGINATION_WINDOW


    result = OrderedDict()
    result['offset'] = offset
    result['limit'] = limit

    if isinstance(data, Query):
        result['total_count'] = data.count()
        if limit != -1:
            result['items'] = data.offset(offset).limit(limit).all()
        else:
            result['items'] = data.offset(offset).all()
        return result
    elif isinstance(data, list):
        result['total_count'] = len(data)
        if limit != -1:
            result['items'] = data[ offset : offset+limit ]
        else:
            result['items'] = data[ offset : ]
        return result
    else:
        return data


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


from lazy import lazy as lazy_property
# import functools
# class lazy_property(object):
#     """lazy descriptor
#     Used as a decorator to create lazy attributes. Lazy attributes
#     are evaluated on first use.
#     """
#
#     def __init__(self, func):
#         self.__func = func
#         functools.wraps(self.__func)(self)
#
#     def __get__(self, inst, inst_cls):
#         if inst is None:
#             return self
#
#         if not hasattr(inst, '__dict__'):
#             raise AttributeError("'%s' object has no attribute '__dict__'" % (inst_cls.__name__,))
#
#         name = self.__name__
#         if name.startswith('__') and not name.endswith('__'):
#             name = '_%s%s' % (inst_cls.__name__, name)
#
#         value = self.__func(inst)
#         inst.__dict__[name] = value
#         return value
#
#     @classmethod
#     def invalidate(cls, inst, name):
#         """Invalidate a lazy attribute.
#         This obviously violates the lazy contract. A subclass of lazy
#         may however have a contract where invalidation is appropriate.
#         """
#         inst_cls = inst.__class__
#
#         if not hasattr(inst, '__dict__'):
#             raise AttributeError("'%s' object has no attribute '__dict__'" % (inst_cls.__name__,))
#
#         if name.startswith('__') and not name.endswith('__'):
#             name = '_%s%s' % (inst_cls.__name__, name)
#
#         if not isinstance(getattr(inst_cls, name), cls):
#             raise AttributeError("'%s.%s' is not a %s attribute" % (inst_cls.__name__, name, cls.__name__))
#
#         if name in inst.__dict__:
#             del inst.__dict__[name]

# class lazy_property(object):
#     """A read only property that caches the initially computed value on demand.
#
#     This descriptor will only call the provided ``fget`` function once.
#     Subsequent access to this property will return the cached value.
#
#     """
#
#     def __init__(self, fget):
#         self._fget = fget
#
#     def __get__(self, obj, cls):
#         if obj is None:
#             return self
#         else:
#             computed_value = self._fget(obj)
#             obj.__dict__[self._fget.__name__] = computed_value
#             return computed_value