# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import warnings
import sqlalchemy as sa

from typing import List, Callable, Optional, Type, Dict, TypeVar, Union, Iterable, Any, Tuple
from functools import partial
from datetime import date, datetime
from django.conf import settings
from django.http import QueryDict
from dataclasses import dataclass
from sqlalchemy import func
from sqlalchemy.sql.functions import Function
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.attributes import QueryableAttribute

from lamb.exc import InvalidParamTypeError, ServerError, InvalidParamValueError, ApiError, InvalidBodyStructureError
from lamb.utils import dpath_value, LambRequest, datetime_begin, datetime_end, compact
from lamb.utils.transformers import transform_date, transform_string_enum, transform_boolean


__all__ = [
    'Filter', 'FieldValueFilter', 'ColumnValueFilter', 'DatetimeFilter', 'EnumFilter',
    'PostgresqlFastTextSearchFilter', 'ColumnBooleanFilter', 'JsonDataFilter'
]

logger = logging.getLogger(__name__)


# abstract
T = TypeVar('T')


# TODO: migrate to dataclasses
class Filter(object):
    """ Abstract filter for model query """

    arg_name: str
    req_type: Type
    req_type_transformer: Optional[Callable]

    def __init__(self, arg_name: str, req_type: Type, req_type_transformer: Callable = None):
        # check params
        if not isinstance(arg_name, str):
            logger.warning('Filter arg_name invalid data type: %s' % arg_name)
            raise ServerError('Improperly configured filter')
        if not isinstance(req_type, type):
            logger.warning('Filter req_type invalid data type: %s' % req_type)
            raise ServerError('Improperly configured filter')
        if req_type_transformer is not None and not callable(req_type_transformer):
            logger.warning('Filter req_type_transformer invalid data type: %s' % req_type_transformer)
            raise ServerError('Improperly configured filter')

        # store values
        self.arg_name = arg_name
        self.req_type = req_type
        self.req_type_transformer = req_type_transformer

    def get_param_value(self, params: Dict, key_path: str = None) -> Optional[List[object]]:
        """ Extracts and convert param value from dictionary """
        # handle key_path default as arg_name
        if key_path is None:
            key_path = self.arg_name

        # extract value
        if isinstance(params, QueryDict):
            result = params.getlist(key_path, default=None)
            if len(result) > 0:
                result = [str(r) for r in result]
                result = ','.join(result)
            else:
                result = None
        else:
            result = dpath_value(params, key_path, str, default=None)
        if result is None:
            return None

        # split values
        result = result.split(',')

        # remove duplicates
        result = list(set(result))

        # convert according to required param type
        try:
            result = [self.req_type(r) if r.lower() != 'null' else None for r in result]
        except ApiError:
            raise
        except Exception as e:
            logger.warning('Param convert error: %s' % e)
            raise InvalidParamTypeError('Invalid data type for param %s' % key_path)

        # convert according to required transformer
        if self.req_type_transformer is not None:
            try:
                result = [self.req_type_transformer(r) if r is not None else None for r in result]
            except ApiError:
                raise
            except Exception as e:
                logger.warning('Param convert error: %s' % e)
                raise InvalidParamTypeError('Could not convert param type to required form %s' % key_path)

        # return result
        return result

    def vary_param_value_equal(self, value: T) -> T:
        return value

    def vary_param_value_not_equal(self, value: T) -> T:
        return value

    def vary_param_value_max(self, value: T) -> T:
        return value

    def vary_param_value_min(self, value: T) -> T:
        return value

    def apply_to_query(self, query: Query, params: Dict = None, **kwargs) -> Query:
        """ Apply filter to query """
        return query


class FieldValueFilter(Filter):
    """ Basic sqlalchemy attribute comparing filter """

    comparing_field: QueryableAttribute
    allowed_compares: List[str]

    def __init__(self, arg_name: str, req_type: type, comparing_field: QueryableAttribute,
                 req_type_transformer: Callable = None,
                 allowed_compares: List[str] = ['__eq__', '__ne__', '__ge__', '__le__']):
        super().__init__(arg_name, req_type, req_type_transformer)

        # check params
        if not isinstance(comparing_field, QueryableAttribute):
            logger.warning('Filter comparing_field invalid data type: %s %s'
                           % (comparing_field, comparing_field.__class__.__name__))
            raise ServerError('Improperly configured filter')

        for c in allowed_compares:
            if c not in ['__eq__', '__ne__', '__lt__', '__le__', '__ge__', '__gt__']:
                logger.warning('Filter allowed_compares invalid data type: %s' % allowed_compares)
                raise ServerError('Improperly configured filter')

        # store attributes
        self.comparing_field = comparing_field
        self.allowed_compares = allowed_compares

    # def apply_to_query(self, query: Query, request: LambRequest = None, params: Dict = None) -> Query:
    def apply_to_query(self, query: Query, params, **kwargs) -> Query:
        # check for equality
        if '__eq__' in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name)
            if param_value is not None:
                if len(param_value) > 1:
                    try:  # check for null value in values
                        param_value.remove(None)
                    except ValueError:
                        query = query.filter(self.comparing_field.in_(param_value))
                    else:
                        # IN (...) OR IS NULL
                        query = query.filter(sa.or_(self.comparing_field.in_(param_value),
                                                    self.comparing_field.__eq__(None)))
                else:
                    query = query.filter(self.comparing_field.__eq__(param_value[0]))

        # check for non equality
        if '__ne__' in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name + '.exclude')
            if param_value is not None:
                if len(param_value) > 1:
                    try:  # check for null value in values
                        param_value.remove(None)
                    except ValueError:
                        query = query.filter(~self.comparing_field.in_(param_value))
                    else:
                        # IN (...) AND IS NOT NULL
                        query = query.filter(sa.and_(~self.comparing_field.in_(param_value),
                                                     self.comparing_field.__ne__(None)))
                else:
                    query = query.filter(self.comparing_field.__ne__(param_value[0]))

        # check for greater
        if '__gt__' in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name + '.greater')
            if param_value is not None:
                if len(param_value) > 1:
                    raise InvalidParamValueError('Invalid param \'%s\' type for greater compare' % self.arg_name)
                param_value = param_value[0]
                param_value = self.vary_param_value_min(value=param_value)
                query = query.filter(self.comparing_field.__gt__(param_value))

        # check for greater or equal
        if '__ge__' in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name + '.min')
            if param_value is not None:
                if len(param_value) > 1:
                    raise InvalidParamValueError('Invalid param \'%s\' type for greater/equal compare' % self.arg_name)
                param_value = param_value[0]
                param_value = self.vary_param_value_min(value=param_value)
                query = query.filter(self.comparing_field.__ge__(param_value))

        # check for lower
        if '__lt__' in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name + '.less')
            if param_value is not None:
                if len(param_value) > 1:
                    raise InvalidParamValueError('Invalid param \'%s\' type for lower compare' % self.arg_name)
                param_value = param_value[0]
                param_value = self.vary_param_value_max(value=param_value)
                query = query.filter(self.comparing_field.__lt__(param_value))

        # check for lower or equal
        if '__le__' in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name + '.max')
            if param_value is not None:
                if len(param_value) > 1:
                    raise InvalidParamValueError('Invalid param \'%s\' type for lower/equal compare' % self.arg_name)
                param_value = param_value[0]
                param_value = self.vary_param_value_max(value=param_value)
                query = query.filter(self.comparing_field.__le__(param_value))

        return query


class ColumnValueFilter(FieldValueFilter):
    """ Syntax sugar for column based simple filter"""

    def __init__(self, column, arg_name=None, req_type=None, **kwargs):
        # predefine params
        ins = sa.inspect(column)

        if arg_name is None:
            # TODO: fix to properly work on hybrid properties and synonims
            arg_name = ins.name

        if req_type is None:
            req_type = ins.type.python_type

        super().__init__(
            arg_name=arg_name,
            req_type=req_type,
            comparing_field=column,
            **kwargs
        )


# special syntax sugars
# def _timestamp_transform_date(value: Union[datetime, date, str, int, float], format=settings.LAMB_RESPONSE_DATE_FORMAT) -> Union[datetime, date]:
#     # try to convert as timestamp
#     if isinstance(value, (str, int, float)):
#         try:
#             float_value = float(value)
#             if len(str(float_value)) >= 11:
#                 float_value = float_value / 1000
#             result = datetime.fromtimestamp(float_value)
#             return result
#         except ValueError:
#             pass
#
#     return transform_date(value, format)


class DatetimeFilter(ColumnValueFilter):

    def __init__(self, *args, fmt=settings.LAMB_RESPONSE_DATE_FORMAT, **kwargs):
        super().__init__(
            *args,
            req_type=str,
            req_type_transformer=partial(transform_date, format=fmt),
            **kwargs
        )

    def vary_param_value_min(self, value: Union[datetime, date]) -> datetime:
        if isinstance(value, datetime):
            return value
        else:
            return datetime_begin(value)

    def vary_param_value_max(self, value: Union[datetime, date]) -> datetime:
        if isinstance(value, datetime):
            return value
        else:
            return datetime_end(value)


class ColumnBooleanFilter(ColumnValueFilter):
    def __init__(self, *args, **kwargs):
        if 'req_type' not in kwargs:
            kwargs['req_type'] = str
        if 'req_type_transformer' not in kwargs:
            kwargs['req_type_transformer'] = transform_boolean
        if 'allowed_compares' not in kwargs:
            kwargs['allowed_compares'] = ['__eq__', '__ne__']

        super().__init__(*args, **kwargs)
        # kwargs['req_type']


class EnumFilter(ColumnValueFilter):

    def __init__(self, column, **kwargs):
        # predefine params
        ins = sa.inspect(column)

        # replace params
        kwargs.pop('req_type', None)
        kwargs.pop('req_type_transformer', None)
        if 'req_type' not in kwargs:
            kwargs['req_type'] = str

        if 'req_type_transformer' not in kwargs:
            ins = sa.inspect(column)
            kwargs['req_type_transformer'] = partial(transform_string_enum, enum_class=ins.type.python_type)

        if 'allowed_compares' not in kwargs:
            kwargs['allowed_compares'] = ['__eq__', '__ne__']

        super().__init__(column, **kwargs)


class PostgresqlFastTextSearchFilter(Filter):
    """
    Fast text search for PostgreSQL filter.
    # TODO: add description
    """

    _tsquery_func: Callable
    _tsvector_expr: Callable
    _reconfig: str

    def __init__(self,
                 columns: Optional[Union[QueryableAttribute, List[QueryableAttribute]]] = None,
                 tsvector_expr: Optional[Any] = None,
                 tsquery_func: Callable[[str], Function] = None,
                 reconfig='russian',
                 arg_name='search_text'
                 ):
        super().__init__(arg_name=arg_name, req_type=str, req_type_transformer=None)

        self._reconfig = reconfig

        # parse tsvector_expr
        if tsvector_expr is not None:
            self._tsvector_expr = tsvector_expr
        elif columns is not None:
            # construct tsvector_expr based on columns
            if not isinstance(columns, (list, tuple)):
                columns = [columns]

            _expr = func.COALESCE(columns[0], '')
            for c in columns[1:]:
                _expr = _expr + ' ' + func.COALESCE(c, '')

            _expr = func.to_tsvector(self._reconfig, _expr)

            self._tsvector_expr = _expr
        else:
            logger.warning('Full text search filter should be initialized with tsvector_expr object or columns')
            raise ServerError('Improperly confiogured full text search filter')

        # parse tsquery_func
        if tsquery_func is None:
            self._tsquery_func = lambda search_string: func.websearch_to_tsquery(self._reconfig, search_string)
        else:
            self._tsquery_func = tsquery_func

    def apply_to_query(self, query: Query, params: Dict, **kwargs) -> Query:
        # extract param
        param_value = self.get_param_value(params=params)
        if param_value is None:
            return query

        # apply search
        if len(param_value) > 0:
            param_value = ','.join(param_value)
        else:
            param_value = param_value[0]

        # do not search over empty
        if len(param_value) == 0:
            return query

        # apply to columns
        query = query.filter(
            self._tsvector_expr.op('@@')(self._tsquery_func(param_value))
        )
        return query


class JsonFilterDescriptor(object):
    """ Json filter descriptor

    :type key_path: list
    :type value: str
    :type comparing_function: str
    """

    def __init__(self, key_path, value, comparing_function):
        super().__init__()
        self.key_path = key_path
        self.value = value
        self.comparing_function = comparing_function

    def __str__(self):
        return 'JsonFilterDescriptor(%s, %s, %s)' % (self.key_path, self.value, self.comparing_function)


class JsonDataFilter(ColumnValueFilter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.req_type = str
        self.req_type_transformer = None

    @staticmethod
    def _parse_descriptor(raw_descriptor):
        """ Parse descriptor to extract parts: key_path, value, functor
        :type raw_descriptor: str
        :rtype: JsonFilterDescriptor
        """
        # parse parts
        functor_mapping = {
            '==': '__eq__',
            '!=': '__ne__'
        }

        result = None

        for delimiter, comparing_function in functor_mapping.items():
            parts = raw_descriptor.split(delimiter)
            parts = compact(parts)
            if len(parts) != 2:
                continue

            result = JsonFilterDescriptor(
                key_path=parts[0],
                value=parts[1],
                comparing_function=comparing_function
            )
            break

        if result is None:
            raise InvalidBodyStructureError(
                'Could not parse json field request descriptor: key_path and value required')

        # convert key path to form of list
        unparsed_key_path = result.key_path
        unparsed_key_path = unparsed_key_path.split('.')

        # convert key path components to include int indices
        buffer = list()
        for path_component in unparsed_key_path:
            try:
                path_component = int(path_component)
            except ValueError:
                pass
            buffer.append(path_component)
        result.key_path = buffer

        # check for special value
        if result.value.lower() == 'null':
            result.value = None

        # return results
        return result

    # def apply_to_query(self, query, request):
    def apply_to_query(self, query: Query, params: Dict, **kwargs) -> Query:
        # early return
        param_value = self.get_param_value(params, key_path=self.arg_name)
        if param_value is None:
            return query

        # apply filters
        for raw_descriptor in param_value:
            descriptor = JsonDataFilter._parse_descriptor(raw_descriptor)

            # construct comparator
            field = self.comparing_field
            for key_path_component in descriptor.key_path:
                field = field[key_path_component]

            if descriptor.comparing_function == '__eq__':
                query = query.filter(field.astext.__eq__(descriptor.value))
            elif descriptor.comparing_function == '__ne__':
                query = query.filter(field.astext.__ne__(descriptor.value))
            else:
                raise InvalidParamValueError('Unsupported comparing function %s' % descriptor.comparing_function)

        return query