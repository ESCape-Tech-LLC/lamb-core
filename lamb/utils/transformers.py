from __future__ import annotations

import re
import enum
import uuid
import logging
import warnings
from typing import List, Type, Union, TypeVar, Optional
from datetime import date, datetime
from functools import singledispatch

# Lamb Framework
from lamb.exc import (
    ApiError,
    ServerError,
    InvalidParamTypeError,
    InvalidParamValueError,
)

import dateutil

__all__ = [
    "transform_boolean",
    "transform_date",
    "transform_datetime",
    "transform_string_enum",
    "transform_uuid",
    "transform_prefixed_tsquery",
    "transform_datetime_seconds_int",
    "transform_datetime_milliseconds_int",
    "transform_datetime_milliseconds_float",
    "transform_datetime_microseconds_int",
    "transform_typed_list",
    "tf_list_int",
    "tf_list_string",
    "tf_list_uuid",
]

logger = logging.getLogger(__name__)

"""

Transformer - is any callable that accepts `value` as first positional argument and converts it to another value

"""


def transform_boolean(value) -> bool:
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        result = value.lower()
        if result in ("1", "true", "yes", "y", "t", "on"):
            return True
        elif result in ("0", "false", "no", "n", "f", "off"):
            return False
        else:
            raise InvalidParamValueError("Invalid value for boolean convert")
    elif isinstance(value, (int, float)):
        return value != 0.0
    else:
        raise InvalidParamTypeError("Invalid data type for boolean convert")


def transform_date(value: Union[datetime, date, str], **kwargs) -> datetime.date:
    return transform_datetime(value, **kwargs).date()


def transform_datetime(value: Union[datetime, date, str, int, float], __format=None, **kwargs) -> datetime:
    from django.conf import settings

    # Lamb Framework
    from lamb.utils import datetime_begin

    if __format is None and "format" in kwargs:
        warnings.warn("transform_date: format keyword is deperectaed, use __format instead", DeprecationWarning)
        __format = kwargs["format"]

    if __format is None:
        __format = settings.LAMB_RESPONSE_DATE_FORMAT

    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime_begin(value)
    elif isinstance(value, (str, int)):
        # try to convert as timestamp
        try:
            float_value = float(value)
            if len(str(round(float_value))) >= 16:
                # int microseconds format
                float_value = float_value / 1000000
            if len(str(round(float_value))) >= 11:
                # inf/float milliseconds format
                float_value = float_value / 1000
            result = datetime.fromtimestamp(float_value)
            return result
        except ValueError:
            pass

        # try to convert according to format
        try:
            if value.lower() == "now":
                result = datetime.now()
            elif value.lower() == "today":
                result = datetime_begin(datetime.now())
            elif __format == "auto":
                result = dateutil.parser.parse(value)
            elif __format == "iso":
                # hack for compatibility with not standard serializers
                _value = value.replace("Z", "+00:00")
                result = datetime.fromisoformat(_value)
            else:
                result = datetime.strptime(value, __format)
            return result
        except Exception as e:
            raise InvalidParamValueError(
                "Invalid to convert date from string=%s according to format=%s" % (value, __format)
            ) from e
    else:
        raise InvalidParamTypeError("Invalid data type for date convert")


def transform_uuid(value: str, key: Optional[str] = None) -> uuid.UUID:
    """Transforms value into UUID version"""
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError) as e:
        raise InvalidParamValueError("Invalid value for uuid field", error_details=key) from e


def transform_prefixed_tsquery(value: str) -> str:
    result = re.sub("[()|&*:!]", " ", value)
    result = " & ".join(result.split())
    if len(result) > 0:
        result += ":*"
    else:
        result = "*"
    return result


def transform_datetime_seconds_int(value: datetime) -> int:
    return int(value.timestamp())


def transform_datetime_milliseconds_int(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def transform_datetime_milliseconds_float(value: datetime) -> float:
    return value.timestamp()


def transform_datetime_microseconds_int(value: datetime) -> int:
    return int(value.timestamp() * 1000000)


# dynamic typed
ET = TypeVar("ET")


def transform_string_enum(value: str, enum_class: Type[ET]) -> ET:
    """Transforms string version into string based Enum"""
    if isinstance(value, enum_class):
        return value

    # check data types
    if not issubclass(enum_class, enum.Enum) and not issubclass(enum_class, str):
        logger.warning("transform_string_enum received object of class %s as enum_class arg" % enum_class)
        raise ServerError("Invalid class type for enum converting")
    if not isinstance(value, str):
        logger.warning("transform_string_enum received object of class %s as value arg" % value.__class__.__name__)
        raise ServerError("Invalid class type for enum converting")

    # try to convert
    try:
        for enum_candidate in enum_class:
            if value.lower() == enum_candidate.value.lower():
                return enum_class(enum_candidate)

        # not found - raise
        raise InvalidParamValueError(f"Could not cast {value} as valid {enum_class.__name__}")
    except ApiError:
        raise
    except Exception as e:
        raise InvalidParamValueError("Failed to convert enum value %s" % value) from e


@singledispatch
def transform_typed_list(
    value: Union[object, ET, List[ET]], cls: Type[ET], convert: bool = False, key: Optional[str] = None, **_
) -> List[ET]:
    if isinstance(value, cls):
        value = [value]

    if not isinstance(value, list):
        raise InvalidParamTypeError(f"Invalid type for {cls.__name__}-list: {value}", error_details=key)

    if convert:
        try:
            value = [cls(i) for i in value]
        except Exception as e:
            raise InvalidParamTypeError(f"Invalid type for {cls.__name__}-list: {value}", error_details=key) from e
    else:
        if any(not isinstance(i, cls) for i in value):
            raise InvalidParamTypeError(f"Invalid type for {cls.__name__}-list: {value}", error_details=key)

    return value


@transform_typed_list.register(str)
def _transform_typed_list(value: str, cls: Type[ET], skip_empty: bool = True, separator: str = ",", **kwargs) -> ET:
    value = value.split(separator)
    if skip_empty:
        value = [v for v in value if len(v) > 0]
    if "convert" not in kwargs:
        kwargs["convert"] = True
    if "cls" not in kwargs:
        kwargs["cls"] = cls
    return transform_typed_list(value, **kwargs)  # forward to main processing


def tf_list_string(value, **kwargs) -> List[str]:
    kwargs["cls"] = str
    if "separator" not in kwargs:
        kwargs["separator"] = ","
    return transform_typed_list(value, **kwargs)


def tf_list_int(value, **kwargs) -> List[int]:
    kwargs["cls"] = int
    return transform_typed_list(value, **kwargs)


def tf_list_uuid(value, **kwargs) -> List[uuid.UUID]:
    kwargs["cls"] = uuid.UUID
    if "convert" not in kwargs:
        kwargs["convert"] = True
    return transform_typed_list(value, **kwargs)
