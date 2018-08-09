# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import abc
import operator

import sqlalchemy as sa
from sqlalchemy.orm.session import Session as SASession
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.attributes import InstrumentedAttribute

from typing import List, Callable

from lamb.exc import InvalidParamTypeError, ServerError, InvalidParamValueError
from lamb.utils import dpath_value, LambRequest
from lamb.db.inspect import ModelInspector


__all__ = [
    'Filter', 'FieldValueFilter', 'ColumnValueFilter'
]

logger = logging.getLogger(__name__)

# abstract
class Filter(object):
    """ Abstract filter for model query """

    def __init__(self, arg_name: str, req_type: type, req_type_transformer: Callable =None):
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

    # def get_param_value(self, params: dict, key_path: str | List[str] = None) -> List[object]:
    def get_param_value(self, params: dict, key_path: str = None) -> List[object]:
        """ Extracts and convert param value from dictionary """
        # handle key_path default as arg_name
        if key_path is None:
            key_path = self.arg_name

        # extract value
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
        except Exception as e:
            logger.warning('Param convert error: %s' % e)
            raise InvalidParamTypeError('Invalid data type for param %s' % key_path)

        # convert according to required tramsformer
        if self.req_type_transformer is not None:
            try:
                result = [self.req_type_transformer(r) if r is not None else None for r in result]
            except:
                logger.warning('Param convert error: %s' % e)
                raise InvalidParamTypeError('Could not convert param type to required form %s' % key_path)

        # return result
        return result

    def apply_to_query(self, query: Query, request: LambRequest) -> Query:
        """ Apply filter to query """
        return query


class FieldValueFilter(Filter):
    """ Basic sqlalchemy attribute comparing filter """

    def __init__(self, arg_name: str, req_type: type, comparing_field: InstrumentedAttribute,
                 req_type_transformer: Callable = None,
                 allowed_compares: List[str] = ['__eq__', '__ne__', '__ge__', '__le__']):
        super().__init__(arg_name, req_type, req_type_transformer)

        # check params
        if not isinstance(comparing_field, InstrumentedAttribute):
            logger.warning('Filter comparing_field invalid data type: %s' % comparing_field)
            raise ServerError('Improperly configured filter')

        for c in allowed_compares:
            if c not in ['__eq__', '__ne__', '__le__', '__ge__']:
                logger.warning('Filter allowed_compares invalid data type: %s' % allowed_compares)
                raise ServerError('Improperly configured filter')

        # store attributes
        self.comparing_field = comparing_field
        self.allowed_compares = allowed_compares

    def apply_to_query(self, query, request):
        """
        :type query: sqlalchemy.orm.query.Query
        :type request: F2CRequest
        """
        # check for equality
        if '__eq__' in self.allowed_compares:
            param_value = self.get_param_value(request.GET, key_path=self.arg_name)
            if param_value is not None:
                if len(param_value) > 1:
                    query = query.filter(self.comparing_field.in_(param_value))
                else:
                    query = query.filter(self.comparing_field.__eq__(param_value[0]))

        # check for non equality
        if '__ne__' in self.allowed_compares:
            param_value = self.get_param_value(request.GET, key_path=self.arg_name + '.exclude')
            if param_value is not None:
                if len(param_value) > 1:
                    query = query.filter(~self.comparing_field.in_(param_value))
                else:
                    query = query.filter(self.comparing_field.__ne__(param_value[0]))

        # check for greater or equal
        if '__ge__' in self.allowed_compares:
            param_value = self.get_param_value(request.GET, key_path=self.arg_name + '.min')
            if param_value is not None:
                if len(param_value) > 1:
                    raise InvalidParamValueError('Invalid param \'%s\' type for greater/equal compare' % self.arg_name)
                param_value = param_value[0]
                query = query.filter(self.comparing_field.__ge__(param_value))

        # check for lower or equal
        if '__le__' in self.allowed_compares:
            param_value = self.get_param_value(request.GET, key_path=self.arg_name + '.max')
            if param_value is not None:
                if len(param_value) > 1:
                    raise InvalidParamValueError('Invalid param \'%s\' type for lower/equal compare' % self.arg_name)
                param_value = param_value[0]
                query = query.filter(self.comparing_field.__le__(param_value))

        return query


class ColumnValueFilter(FieldValueFilter):
    """ Syntax sugar for column based simple filter"""

    def __init__(self, column, **kwargs):
        # predefine params
        ins = sa.inspect(column)
        column_name = ins.name
        column_type = ins.type.python_type
        updated_kwargs = {
            'arg_name': ins.name,
            'req_type': ins.type.python_type
        }

        # update params and call super
        updated_kwargs.update(kwargs)
        super().__init__(**kwargs)
