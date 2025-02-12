from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from datetime import date, datetime
from functools import partial
from typing import Any, TypeVar

import sqlalchemy as sa
from django.conf import settings
from django.http import QueryDict
from sqlalchemy import Float, func
from sqlalchemy.dialects.postgresql import DOMAIN
from sqlalchemy.orm.attributes import QueryableAttribute
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.functions import Function

from lamb.exc import (
    ApiError,
    InvalidBodyStructureError,
    InvalidParamTypeError,
    InvalidParamValueError,
    ServerError,
)
from lamb.utils import datetime_begin, datetime_end, dpath_value
from lamb.utils.core import compact
from lamb.utils.transformers import (
    transform_boolean,
    transform_date,
    transform_datetime,
    transform_string_enum,
)

__all__ = [
    "Filter",
    "FieldValueFilter",
    "ColumnValueFilter",
    "DateFilter",
    "DatetimeFilter",
    "EnumFilter",
    "PostgresqlFastTextSearchFilter",
    "ColumnBooleanFilter",
    "JsonDataFilter",
]

logger = logging.getLogger(__name__)

# abstract
T = TypeVar("T")


# TODO: migrate to dataclasses
class Filter:
    """Abstract filter for model query"""

    arg_name: str
    req_type: type
    req_type_transformer: Callable | None

    def __init__(self, arg_name: str, req_type: type, req_type_transformer: Callable = None):
        # check params
        if not isinstance(arg_name, str):
            logger.warning(f"Filter arg_name invalid data type: {arg_name}")
            raise ServerError("Improperly configured filter")
        if not isinstance(req_type, type):
            logger.warning(f"Filter req_type invalid data type: {req_type}")
            raise ServerError("Improperly configured filter")
        if req_type_transformer is not None and not callable(req_type_transformer):
            logger.warning(f"Filter req_type_transformer invalid data type: {req_type_transformer}")
            raise ServerError("Improperly configured filter")

        # store values
        self.arg_name = arg_name
        self.req_type = req_type
        self.req_type_transformer = req_type_transformer

    def get_param_value(self, params: dict, key_path: str = None) -> list[object] | None:
        """Extracts and convert param value from dictionary"""
        # handle key_path default as arg_name
        if key_path is None:
            key_path = self.arg_name

        # extract value
        if isinstance(params, QueryDict):
            result = params.getlist(key_path, default=None)
            if len(result) > 0:
                result = [str(r) for r in result]
                result = ",".join(result)
            else:
                result = None
        else:
            result = dpath_value(params, key_path, str, default=None)
        if result is None:
            return None

        # split values
        result = result.split(",")

        # remove duplicates
        result = list(set(result))

        # convert according to required param type
        try:
            result = [self.req_type(r) if r.lower() != "null" else None for r in result]
        except ApiError:
            raise
        except Exception as e:
            logger.warning(f"Param convert error: {e}")
            raise InvalidParamTypeError(f"Invalid data type for param {key_path}") from e

        # convert according to required transformer
        if self.req_type_transformer is not None:
            try:
                result = [self.req_type_transformer(r) if r is not None else None for r in result]
            except ApiError:
                raise
            except Exception as e:
                logger.warning(f"Param convert error: {e}")
                raise InvalidParamTypeError(f"Could not convert param type to required form {key_path}") from e

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

    def apply_to_query(self, query: Query, params: dict = None, **kwargs) -> Query:
        """Apply filter to query"""
        return query


class FieldValueFilter(Filter):
    """Basic sqlalchemy attribute comparing filter"""

    comparing_field: QueryableAttribute
    allowed_compares: list[str]

    def __init__(
        self,
        arg_name: str,
        req_type: type,
        comparing_field: QueryableAttribute,
        req_type_transformer: Callable = None,
        allowed_compares: list[str] | None = None,
    ):
        allowed_compares = allowed_compares or ["__eq__", "__ne__", "__ge__", "__le__"]
        super().__init__(arg_name, req_type, req_type_transformer)

        # check params
        if not isinstance(comparing_field, QueryableAttribute):
            logger.warning(
                f"Filter comparing_field invalid data type: {comparing_field} {comparing_field.__class__.__name__}"
            )
            raise ServerError("Improperly configured filter")

        for c in allowed_compares:
            if c not in ["__eq__", "__ne__", "__lt__", "__le__", "__ge__", "__gt__"]:
                logger.warning(f"Filter allowed_compares invalid data type: {allowed_compares}")
                raise ServerError("Improperly configured filter")

        # store attributes
        self.comparing_field = comparing_field
        self.allowed_compares = allowed_compares

    # def apply_to_query(self, query: Query, request: LambRequest = None, params: Dict = None) -> Query:
    def apply_to_query(self, query: Query, params, **kwargs) -> Query:
        # check for equality
        if "__eq__" in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name)
            if param_value is not None:
                if len(param_value) > 1:
                    try:  # check for null value in values
                        param_value.remove(None)
                    except ValueError:
                        query = query.filter(self.comparing_field.in_(param_value))
                    else:
                        # IN (...) OR IS NULL
                        query = query.filter(
                            sa.or_(self.comparing_field.in_(param_value), self.comparing_field.__eq__(None))
                        )
                else:
                    query = query.filter(self.comparing_field.__eq__(param_value[0]))

        # check for non equality
        if "__ne__" in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name + ".exclude")
            if param_value is not None:
                if len(param_value) > 1:
                    try:  # check for null value in values
                        param_value.remove(None)
                    except ValueError:
                        query = query.filter(~self.comparing_field.in_(param_value))
                    else:
                        # IN (...) AND IS NOT NULL
                        query = query.filter(
                            sa.and_(~self.comparing_field.in_(param_value), self.comparing_field.__ne__(None))
                        )
                else:
                    query = query.filter(self.comparing_field.__ne__(param_value[0]))

        # check for greater
        if "__gt__" in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name + ".greater")
            if param_value is not None:
                if len(param_value) > 1:
                    raise InvalidParamValueError(f"Invalid param '{self.arg_name}' type for greater compare")
                param_value = param_value[0]
                param_value = self.vary_param_value_min(value=param_value)
                query = query.filter(self.comparing_field.__gt__(param_value))

        # check for greater or equal
        if "__ge__" in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name + ".min")
            if param_value is not None:
                if len(param_value) > 1:
                    raise InvalidParamValueError(f"Invalid param '{self.arg_name}' type for greater/equal compare")
                param_value = param_value[0]
                param_value = self.vary_param_value_min(value=param_value)
                query = query.filter(self.comparing_field.__ge__(param_value))

        # check for lower
        if "__lt__" in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name + ".less")
            if param_value is not None:
                if len(param_value) > 1:
                    raise InvalidParamValueError(f"Invalid param '{self.arg_name}' type for lower compare")
                param_value = param_value[0]
                param_value = self.vary_param_value_max(value=param_value)
                query = query.filter(self.comparing_field.__lt__(param_value))

        # check for lower or equal
        if "__le__" in self.allowed_compares:
            param_value = self.get_param_value(params, key_path=self.arg_name + ".max")
            if param_value is not None:
                if len(param_value) > 1:
                    raise InvalidParamValueError(f"Invalid param '{self.arg_name}' type for lower/equal compare")
                param_value = param_value[0]
                param_value = self.vary_param_value_max(value=param_value)
                query = query.filter(self.comparing_field.__le__(param_value))

        return query

    def __str__(self):
        return f"<{self.__class__.__name__}: arg={self.arg_name}, type={self.req_type}, field={self.comparing_field}, tf={self.req_type_transformer}, compares={self.allowed_compares}>"


class ColumnValueFilter(FieldValueFilter):
    """Syntax sugar for column based simple filter"""

    def __init__(self, column, arg_name=None, req_type=None, **kwargs):
        # predefine params
        ins = sa.inspect(column)

        if arg_name is None:
            # TODO: fix to properly work on hybrid properties and synonims
            arg_name = ins.name

        if req_type is None:
            req_type = ins.type.data_type.python_type if isinstance(ins.type, DOMAIN) else ins.type.python_type

        super().__init__(arg_name=arg_name, req_type=req_type, comparing_field=column, **kwargs)


# special syntax sugars
class DateFilter(ColumnValueFilter):
    def __init__(self, *args, fmt=settings.LAMB_RESPONSE_DATE_FORMAT, **kwargs):
        super().__init__(*args, req_type=str, req_type_transformer=partial(transform_date, format=fmt), **kwargs)

    def vary_param_value_min(self, value: datetime | date) -> datetime:
        if isinstance(value, datetime):
            return value
        else:
            return datetime_begin(value)

    def vary_param_value_max(self, value: datetime | date) -> datetime:
        if isinstance(value, datetime):
            return value
        else:
            return datetime_end(value)


class DatetimeFilter(ColumnValueFilter):
    def __init__(self, *args, fmt="iso", **kwargs):
        super().__init__(*args, req_type=str, req_type_transformer=partial(transform_datetime, format=fmt), **kwargs)

    def vary_param_value_min(self, value: datetime | date) -> datetime:
        if isinstance(value, datetime):
            return value
        else:
            return datetime_begin(value)

    def vary_param_value_max(self, value: datetime | date) -> datetime:
        if isinstance(value, datetime):
            return value
        else:
            return datetime_end(value)


class ColumnBooleanFilter(ColumnValueFilter):
    def __init__(self, *args, **kwargs):
        if "req_type" not in kwargs:
            kwargs["req_type"] = str
        if "req_type_transformer" not in kwargs:
            kwargs["req_type_transformer"] = transform_boolean
        if "allowed_compares" not in kwargs:
            kwargs["allowed_compares"] = ["__eq__", "__ne__"]

        super().__init__(*args, **kwargs)
        # kwargs['req_type']


class EnumFilter(ColumnValueFilter):
    def __init__(self, column, **kwargs):
        # predefine params
        ins = sa.inspect(column)

        # replace params
        kwargs.pop("req_type", None)
        kwargs.pop("req_type_transformer", None)
        if "req_type" not in kwargs:
            kwargs["req_type"] = str

        if "req_type_transformer" not in kwargs:
            ins = sa.inspect(column)
            kwargs["req_type_transformer"] = partial(transform_string_enum, enum_class=ins.type.python_type)

        if "allowed_compares" not in kwargs:
            kwargs["allowed_compares"] = ["__eq__", "__ne__"]

        super().__init__(column, **kwargs)


class PostgresqlFastTextSearchFilter(Filter):
    """
    Fast text search for PostgreSQL filter.
    # TODO: add description
    """

    _tsquery_func: Callable
    _tsvector_expr: Callable
    _reconfig: str

    def __init__(
        self,
        columns: QueryableAttribute | list[QueryableAttribute] | None = None,
        tsvector_expr: Any | None = None,
        tsquery_func: Callable[[str], Function] = None,
        reconfig="russian",
        arg_name="search_text",
    ):
        super().__init__(arg_name=arg_name, req_type=str, req_type_transformer=None)

        self._reconfig = reconfig

        # parse tsvector_expr
        if tsvector_expr is not None:
            self._tsvector_expr = tsvector_expr
        elif columns is not None:
            # construct tsvector_expr based on columns
            if not isinstance(columns, list | tuple):
                columns = [columns]

            _expr = func.COALESCE(columns[0], "")
            for c in columns[1:]:
                _expr = _expr + " " + func.COALESCE(c, "")

            _expr = func.to_tsvector(self._reconfig, _expr)

            self._tsvector_expr = _expr
        else:
            logger.warning("Full text search filter should be initialized with tsvector_expr object or columns")
            raise ServerError("Improperly confiogured full text search filter")

        # parse tsquery_func
        if tsquery_func is None:
            self._tsquery_func = lambda search_string: func.websearch_to_tsquery(self._reconfig, search_string)
        else:
            self._tsquery_func = tsquery_func

    def apply_to_query(self, query: Query, params: dict, **kwargs) -> Query:
        # extract param
        param_value = self.get_param_value(params=params)
        if param_value is None:
            return query

        # apply search
        param_value = ",".join(param_value) if len(param_value) > 0 else param_value[0]

        # do not search over empty
        if len(param_value) == 0:
            return query

        # apply to columns
        query = query.filter(self._tsvector_expr.op("@@")(self._tsquery_func(param_value)))
        return query


class JsonFilterDescriptor:
    """Json filter descriptor

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
        return f"JsonFilterDescriptor({self.key_path}, {self.value}, {self.comparing_function})"


class JsonDataFilter(ColumnValueFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.req_type = str
        self.req_type_transformer = kwargs.get("req_type_transformer")

    @staticmethod
    def _parse_descriptor(raw_descriptor):
        """Parse descriptor to extract parts: key_path, value, functor
        :type raw_descriptor: str
        :rtype: JsonFilterDescriptor
        """
        # parse parts
        functor_mapping = {
            "==": "__eq__",
            "!=": "__ne__",
            "<=": "__le__",
            ">=": "__ge__",
            "<": "__lt__",
            ">": "__gt__",
        }

        result = None

        for delimiter, comparing_function in functor_mapping.items():
            parts = raw_descriptor.split(delimiter)
            parts = compact(parts)
            if len(parts) != 2:
                continue

            result = JsonFilterDescriptor(key_path=parts[0], value=parts[1], comparing_function=comparing_function)
            break

        if result is None:
            raise InvalidBodyStructureError(
                "Could not parse json field request descriptor: key_path and value required"
            )

        # convert key path to form of list
        unparsed_key_path = result.key_path
        unparsed_key_path = unparsed_key_path.split(".")

        # convert key path components to include int indices
        buffer = list()
        for path_component in unparsed_key_path:
            with contextlib.suppress(ValueError):
                path_component = int(path_component)
            buffer.append(path_component)
        result.key_path = buffer

        # check for special value
        if result.value.lower() == "null":
            result.value = None

        # return results
        return result

    # def apply_to_query(self, query, request):
    def apply_to_query(self, query: Query, params: dict, **kwargs) -> Query:
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

            if descriptor.comparing_function == "__eq__":
                query = query.filter(field.astext.__eq__(descriptor.value))
            elif descriptor.comparing_function == "__ne__":
                query = query.filter(field.astext.__ne__(descriptor.value))
            elif descriptor.comparing_function == "__lt__":
                query = query.filter(field.astext.cast(Float).__lt__(descriptor.value))
            elif descriptor.comparing_function == "__le__":
                query = query.filter(field.astext.cast(Float).__le__(descriptor.value))
            elif descriptor.comparing_function == "__ge__":
                query = query.filter(field.astext.cast(Float).__ge__(descriptor.value))
            elif descriptor.comparing_function == "__gt__":
                query = query.filter(field.astext.cast(Float).__gt__(descriptor.value))
            else:
                raise InvalidParamValueError(f"Unsupported comparing function {descriptor.comparing_function}")

        return query
