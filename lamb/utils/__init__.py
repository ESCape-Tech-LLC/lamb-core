from __future__ import annotations

import asyncio
import base64
import dataclasses
import enum
import functools
import io
import json
import logging
import re
import sys
import tempfile
import warnings
import zoneinfo
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from inspect import isclass
from typing import Any, Awaitable, BinaryIO, TypedDict, TypeVar
from urllib.parse import unquote
from xml.etree import cElementTree

import requests
import sqlalchemy
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from django.utils import timezone as d_timezone
from PIL import Image as PILImage
from sqlalchemy import Column, Select, asc, desc
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import ColumnProperty, Query
from sqlalchemy.orm.attributes import InstrumentedAttribute, QueryableAttribute

from lamb.utils.core import lazy

try:
    import cassandra
    from cassandra.cqlengine.query import ModelQuerySet
except ImportError:
    cassandra = None
    ModelQuerySet = None


import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession as SAAsyncSession

from lamb.exc import (
    ApiError,
    ExternalServiceError,
    ImproperlyConfiguredError,
    InvalidBodyStructureError,
    InvalidParamTypeError,
    InvalidParamValueError,
    ProgrammingError,
    RequestBodyTooBigError,
    ServerError,
)
from lamb.middleware.grequest import LambGRequestMiddleware
from lamb.utils.core import (
    DeprecationClassHelper,
    DeprecationClassMixin,
    compact,
    get_redis_url,
    import_by_name,
    list_chunks,
    masked_dict,
    masked_url,
    random_string,
)

from .dpath import dpath_value

__all__ = [
    "DeprecationClassHelper",
    "DeprecationClassMixin",
    "compact",
    "import_by_name",
    "random_string",
    "masked_url",
    "masked_dict",
    "get_redis_url",
    "list_chunks",
    "LambRequest",
    "parse_body_as_json",
    "dpath_value",
    "a_response_paginated",
    "response_paginated",
    "response_sorted",
    "response_filtered",
    "get_request_body_encoding",
    "get_request_accept_encoding",
    "get_current_request",
    "CONTENT_ENCODING_XML",
    "CONTENT_ENCODING_JSON",
    "CONTENT_ENCODING_MULTIPART",
    "dpath_value",
    "inject_app_defaults",
    "get_settings_value",
    "datetime_end",
    "datetime_begin",
    "check_device_info_versions_above",
    "timed_lru_cache",
    "timed_lru_cache_clear",
    "async_download_resources",
    "async_download_images",
    "async_request_urls",
    "image_convert_to_rgb",
    "file_is_svg",
    "image_decode_base64",
    "str_coercible",
    "get_columns",
    "get_primary_keys",
    "get_file_mime_type",
    "tz_now",
    "TZ_MSK",
    "TZ_UTC",
    "humanize_bytes",
    "bank_card_type_parse",
]


logger = logging.getLogger(__name__)


class LambRequest(HttpRequest):
    """Class used only for proper type hinting in pycharm, does not guarantee that properties will exist
    :type lamb_db_session_map: dict[str, sqlalchemy.orm.Session | sqlalchemy.ext.asyncio.AsyncSession] | None
    :type lamb_db_session: sqlalchemy.orm.Session | sqlalchemy.ext.asyncio.AsyncSession | None
    :type lamb_execution_meter: lamb.execution_time.ExecutionTimeMeter | None
    :type lamb_device_info: lamb.types.DeviceInfo | None
    :type lamb_locale: lamb.types.LambLocale | None
    :type xray: uuid.UUID | None
    :type xline: uuid.UUID | None
    """

    def __init__(self):
        super().__init__()
        self.lamb_db_session_map = None
        self.lamb_db_session = None
        self.lamb_execution_meter = None
        self.lamb_device_info = None
        self.lamb_locale = None
        self.xray = None
        self.xline = None


# parsing
def parse_body_as_json(request: HttpRequest) -> dict | list:
    """Parse request object to dictionary as JSON

    :param request: Request object

    :return:  Body parsed as JSON object

    :raises InvalidBodyStructureError: In case of parsing failed or parsed object is not dictionary
    """
    try:
        body = request.body
    except RequestDataTooBig as e:
        raise RequestBodyTooBigError() from e
    except Exception as e:
        raise ServerError("Invalid request object") from e

    try:
        data = json.loads(body)
        if not isinstance(data, (dict | list)):
            raise InvalidBodyStructureError("JSON body of request should be represented in a form of dictionary/array")
        return data
    except ValueError as e:
        raise InvalidBodyStructureError("Could not parse body as JSON object") from e


# response utilities

PV = TypeVar("PV", list, Query, ModelQuerySet, Select)
_T = TypeVar("_T", bound=Any)

# TODO: move in external module
# TODO: support for different kind of paginations - naive(offset/limit), min value based, token based
# TODO: implement extended as paginator subclass
# TODO: remove result key variations - should be realized on project level base
# TODO: provide ability to override total calculator for known cases


@dataclasses.dataclass(frozen=True)
class _PaginationParams:
    offset: int
    limit: int
    total_omit: bool
    extend_include: bool
    extend_offset: int
    extend_limit: int


class PaginationResult(TypedDict):
    total_count: int | None
    offset: int
    limit: int
    items: list[_T]


def _response_pagination_params(
    request: LambRequest | None = None,
    params: dict | None = None,
    extend_include: bool = False,
) -> _PaginationParams:
    # TODO: move outside of utils to omit cycle loading
    from lamb.utils.transformers import transform_boolean
    from lamb.utils.validators import validate_range

    # extract params
    if request is None and params is None:
        logger.error("Either request or params should be provided")
        raise ProgrammingError
    if request is not None and params is None:
        params = request.GET

    # total omit
    total_omit = dpath_value(
        params,
        settings.LAMB_PAGINATION_KEY_OMIT_TOTAL,
        str,
        transform=transform_boolean,
        default=False,
    )

    # offset
    # TODO: customize validators error raising to provide message and details within from dpath_value
    offset = dpath_value(params, settings.LAMB_PAGINATION_KEY_OFFSET, int, default=0)
    if offset < 0:
        raise InvalidParamValueError(
            "Invalid offset value for pagination", error_details={"key": settings.LAMB_PAGINATION_KEY_OFFSET}
        )

    # limit
    limit = dpath_value(params, settings.LAMB_PAGINATION_KEY_LIMIT, int, default=settings.LAMB_PAGINATION_LIMIT_DEFAULT)
    if limit < -1:
        raise InvalidParamValueError(
            "Invalid limit value for pagination", error_details={"key": settings.LAMB_PAGINATION_KEY_LIMIT}
        )
    if limit > settings.LAMB_PAGINATION_LIMIT_MAX:
        raise InvalidParamValueError(
            "Invalid limit value for pagination - exceed max available",
            error_details={"key": settings.LAMB_PAGINATION_KEY_LIMIT},
        )

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

    return _PaginationParams(
        total_omit=total_omit,
        offset=offset,
        limit=limit if limit != -1 else None,
        extend_offset=extended_offset,
        extend_limit=extended_limit,
        extend_include=extend_include,
    )


async def a_response_paginated(
    collection: PV,
    params: dict = None,
    db_session: SAAsyncSession = None,  # alchemy session
    count_expr: Callable[[PV], Awaitable[int]] | None = None,
    db_as_rows: bool = False,
) -> PaginationResult:
    # prepare
    _p = _response_pagination_params(params=params)
    offset = _p.offset
    limit = _p.limit
    total_omit = _p.total_omit

    # prepare result container
    result = {
        settings.LAMB_PAGINATION_KEY_TOTAL: None,
        settings.LAMB_PAGINATION_KEY_OFFSET: offset,
        settings.LAMB_PAGINATION_KEY_LIMIT: limit,
        settings.LAMB_PAGINATION_KEY_ITEMS: [],
    }

    if isinstance(collection, Select):
        # alchemy 2.0
        if db_session is None:
            logger.error("db_session cannot be None for Select pagination")
            raise ProgrammingError

        if not total_omit:
            # # previous
            # result[settings.LAMB_PAGINATION_KEY_TOTAL] = await db_session.scalar(
            #     sa.select(sa.func.count()).select_from(collection)
            # )
            # new
            # - use subquery version for sqlalchemy deprecation compatibility
            # - removes order_by to omit sorting step not required in count
            if count_expr is None:
                result[settings.LAMB_PAGINATION_KEY_TOTAL] = await db_session.scalar(
                    sa.select(sa.func.count()).select_from(collection.order_by(None).subquery())
                )
            else:
                result[settings.LAMB_PAGINATION_KEY_TOTAL] = await count_expr(collection)

        collection = collection.offset(offset)
        if limit:
            collection = collection.limit(limit)

        if not db_as_rows:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = (await db_session.scalars(collection)).all()
        else:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = (await db_session.execute(collection)).all()
    elif isinstance(collection, list):
        result[settings.LAMB_PAGINATION_KEY_TOTAL] = len(collection) if not total_omit else None

        if limit:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = collection[offset : offset + limit]
        else:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = collection[offset:]
    # elif cassandra is not None and isinstance(collection, ModelQuerySet):
    #     # Cassandra
    #     # NOTE: not checked - uncomment and check in case of usage
    #     result[settings.LAMB_PAGINATION_KEY_TOTAL] = await collection.count() if not total_omit else None
    #     if limit == -1:
    #         result[settings.LAMB_PAGINATION_KEY_ITEMS] = await collection.all()[offset:]
    #     else:
    #         result[settings.LAMB_PAGINATION_KEY_ITEMS] = await collection.all()[offset: offset + limit]
    else:
        logger.error(f"Unsupported collection type for async pagination: {collection.__class__}={collection}")
        raise NotImplementedError

    return result


def response_paginated(
    data: PV,
    request: LambRequest = None,
    params: dict = None,
    add_extended_query: bool = False,
) -> PaginationResult:
    """Pagination utility

    Will search for limit/offset params in `request.GET` object and apply it to data, returning
    dictionary that includes info about real offset, limit, total_count, items.

    :param data: Instance of list or query to be paginated
    :param request: Http request (deprecated version)
    :param params: Dictionary with params of pagination
    :param add_extended_query: Flag to add to result extended version of data slice
        (including one more item from begin and and of slice)
    """
    # extract params
    from lamb.utils.transformers import transform_boolean

    if request is not None and params is None:
        params = request.GET

    total_omit = dpath_value(
        params,
        settings.LAMB_PAGINATION_KEY_OMIT_TOTAL,
        str,
        transform=transform_boolean,
        default=False,
    )

    offset = dpath_value(params, settings.LAMB_PAGINATION_KEY_OFFSET, int, default=0)
    if offset < 0:
        raise InvalidParamValueError(
            "Invalid offset value for pagination", error_details=settings.LAMB_PAGINATION_KEY_OFFSET
        )

    limit = dpath_value(params, settings.LAMB_PAGINATION_KEY_LIMIT, int, default=settings.LAMB_PAGINATION_LIMIT_DEFAULT)
    if limit < -1:
        raise InvalidParamValueError(
            "Invalid limit value for pagination", error_details=settings.LAMB_PAGINATION_KEY_LIMIT
        )
    if limit > settings.LAMB_PAGINATION_LIMIT_MAX:
        raise InvalidParamValueError(
            "Invalid limit value for pagination - exceed max available",
            error_details=settings.LAMB_PAGINATION_KEY_LIMIT,
        )

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
        # SQL
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
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = (
                    data.offset(extended_offset).limit(extended_limit).all()
                )
    elif cassandra is not None and isinstance(data, ModelQuerySet):
        # Cassandra

        result[settings.LAMB_PAGINATION_KEY_TOTAL] = data.count() if not total_omit else None
        if limit == -1:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data.all()[offset:]
        else:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data.all()[offset : offset + limit]
    elif isinstance(data, list):
        # List

        if not total_omit:
            result[settings.LAMB_PAGINATION_KEY_TOTAL] = len(data)
        else:
            result[settings.LAMB_PAGINATION_KEY_TOTAL] = None

        if limit == -1:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data[offset:]
        else:
            result[settings.LAMB_PAGINATION_KEY_ITEMS] = data[offset : offset + limit]

        if add_extended_query:
            if extended_limit == -1:
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = data[offset:]
            else:
                result[settings.LAMB_PAGINATION_KEY_ITEMS_EXTENDED] = data[
                    extended_offset : extended_offset + extended_limit
                ]
    else:
        result = data

    return result


Sorter = tuple[str, Callable]


def _get_instance_sorting_attribute_names(ins: object) -> list[str]:
    # TODO: add support for instance and model class params
    # TODO: cache results
    # discover sortable attributes
    sortable_attributes = set()

    # append columns
    sortable_attributes.update(set(ins.mapper.column_attrs.values()))

    # append hybrid attributes
    sortable_attributes.update(
        set([ormd for ormd in ins.all_orm_descriptors if type(ormd) == hybrid_property])  # noqa: E721
    )

    result = []
    for ormd in sortable_attributes:
        if isinstance(ormd, Column):
            orm_attr_name = ormd.name
        elif isinstance(ormd, ColumnProperty | QueryableAttribute):
            orm_attr_name = ormd.key
        elif isinstance(ormd, hybrid_property):
            orm_attr_name = ormd.__name__
        else:
            logger.warning(f"Unsupported orm_descriptor type: {ormd, ormd.__class__}")
            raise ServerError("Could not serialize data")
        result.append(orm_attr_name)

    return result


def _sorting_parse_sorter(raw_sorting_descriptor: str, model_inspection) -> Sorter:
    """Parse single sorting descriptor"""
    # check against regex and extract field and function
    full_regex = re.compile(r"^\w+{\w+}$")
    short_regex = re.compile(r"^\w+$")
    if full_regex.match(raw_sorting_descriptor) is not None:
        index = raw_sorting_descriptor.index("{")
        field = raw_sorting_descriptor[:index]
        sort_functor = raw_sorting_descriptor[index + 1 : -1]
    elif short_regex.match(raw_sorting_descriptor) is not None:
        field = raw_sorting_descriptor
        sort_functor = "desc"
    else:
        raise InvalidParamValueError(
            f"Invalid sorting descriptor format {raw_sorting_descriptor}",
            error_details={"key_path": "sorting", "descriptor": raw_sorting_descriptor},
        )

    # check against meta data
    sortable_attributes = _get_instance_sorting_attribute_names(model_inspection)
    field = field.lower()
    if field not in sortable_attributes:
        raise InvalidParamValueError(
            f"Invalid sorting_field value for descriptor {raw_sorting_descriptor}. Not found in model",
            error_details={"key_path": "sorting", "descriptor": raw_sorting_descriptor, "field": field},
        )

    sort_functor = sort_functor.lower()
    if sort_functor not in ["asc", "desc"]:
        raise InvalidParamValueError(
            f"Invalid sorting_direction value for descriptor {raw_sorting_descriptor}. Should be one [asc or desc]",
            error_details={"key_path": "sorting", "descriptor": raw_sorting_descriptor},
        )

    sort_functor = asc if sort_functor == "asc" else desc

    return field, sort_functor


def _sorting_parse_descriptors(raw_sorting_descriptors: str | None, model_inspection) -> list[Sorter]:
    """Parse list of sorting descriptors"""
    # early return and check params
    if raw_sorting_descriptors is None:
        return []
    if not isinstance(raw_sorting_descriptors, str):
        logger.warning(f"Invalid sorting descriptors type received: {raw_sorting_descriptors}")
        raise InvalidParamTypeError("Invalid sorting descriptors type")
    raw_sorting_descriptors = unquote(raw_sorting_descriptors)  # dirty hack for invalid arg transfer
    raw_sorting_descriptors = raw_sorting_descriptors.lower()

    # parse data
    sorting_descriptors_list = raw_sorting_descriptors.split(",")
    sorting_descriptors_list = [sd for sd in sorting_descriptors_list if len(sd) > 0]
    result = []
    for sd in sorting_descriptors_list:
        result.append(_sorting_parse_sorter(sd, model_inspection))
    return result


def _sorting_apply_sorters(
    sorters: list[Sorter],
    query: Query,
    model_class: DeclarativeMeta,
    check_duplicate: bool = True,
) -> Query:
    applied_sort_fields: list[str] = list()
    for _sorting_field, _sorting_functor in sorters:
        if _sorting_field in applied_sort_fields and check_duplicate:
            logger.debug(f"skip duplicate sorting field: {_sorting_field}")
            continue
        logger.debug(f"apply sorter: {_sorting_field, _sorting_functor}")
        query = query.order_by(_sorting_functor(getattr(model_class, _sorting_field)))
        applied_sort_fields.append(_sorting_field)
    return query


SV = TypeVar("SV", Query, Select)


def response_sorted(
    query: SV,
    model_class: DeclarativeMeta,
    params: dict,
    default_sorting: str = None,
    **kwargs,
) -> SV:
    """Apply order by sortings to sqlalchemy query instance from params dictionary

    :param query: SQLAlchemy query instance to be sorted
    :param model_class: Model class for columns introspection
    :param params: Dictionary that contains params of sorting
    :param default_sorting: Default sorting descriptors
    :param final_sorting: Final step sorting - if provided in kwargs it would be parsed as descriptor and applied
        to query. By default final step of sorting - is to sort via primary key of model class.
    :param start_sorting: Initial sorting step - if provided in kwargs it would be parsed as descriptor and applied
        to query before all other descriptors.
    """
    # check params
    if not isinstance(params, dict):
        raise ServerError("Improperly configured sorting params dictionary")
    if not isinstance(model_class, DeclarativeMeta):
        raise ServerError("Improperly configured model class meta-data for sorting introspection")
    if not isinstance(query, Query | Select):
        raise ServerError("Improperly configured query item for sorting")

    # prepare inspection and container
    model_inspection = inspect(model_class)

    # discover and apply start sorters
    all_sorters: list[Sorter] = []
    start_sorters = _sorting_parse_descriptors(
        raw_sorting_descriptors=kwargs.get("start_sorting"), model_inspection=model_inspection
    )
    logger.debug(f"sorters parsed start_sorting: {start_sorters}")
    all_sorters.extend(start_sorters)

    # discover and apply client sorters
    client_sorters = _sorting_parse_descriptors(
        raw_sorting_descriptors=dpath_value(params, settings.LAMB_SORTING_KEY, str, default=default_sorting),
        model_inspection=model_inspection,
    )
    logger.debug(f"sorters parsed client_sorters: {client_sorters}")
    all_sorters.extend(client_sorters)

    # discover and apply final sorters
    final_sorters = []
    if "final_sorting" in kwargs:
        # final_sorting exist - should parse and apply descriptors
        final_sorting_descriptors = kwargs["final_sorting"]
        if final_sorting_descriptors is not None:
            final_sorters = _sorting_parse_descriptors(
                raw_sorting_descriptors=final_sorting_descriptors, model_inspection=model_inspection
            )
            logger.debug(f"sorters parsed final_sorters [explicit]: {final_sorters}")
    else:
        # if final sorting omitted - use primary key
        primary_key_columns = [c.name for c in model_inspection.primary_key]
        primary_key_descriptors = ",".join([f"{pk_column}{{desc}}" for pk_column in primary_key_columns])
        primary_key_sorters = _sorting_parse_descriptors(
            raw_sorting_descriptors=primary_key_descriptors, model_inspection=model_inspection
        )
        logger.debug(f"sorters parsed final_sorters [implicit pkey]: {final_sorters}")
        final_sorters = primary_key_sorters

    # apply sorters
    all_sorters.extend(final_sorters)
    query = _sorting_apply_sorters(sorters=all_sorters, query=query, model_class=model_class, check_duplicate=True)

    return query


def response_filtered(
    query: SV,
    filters: list[object],
    request: LambRequest = None,
    params: dict = None,
) -> SV:
    # TODO: fix typing for filters
    # TODO: auto discover request params if not provided
    # import lamb.utils.filters
    # from lamb.utils.filters import Filter
    # filters: List[Filter] = filters
    # check params override
    from lamb.utils.filters import Filter

    if request is not None and params is None:
        params = request.GET

    if not isinstance(query, Query | Select):
        logger.warning(f"Invalid query data type: {query}")
        raise ServerError("Improperly configured query item for filtering")

    for f in filters:
        if not isinstance(f, Filter):
            logger.warning(f"Invalid filters item data type: {f}")
            raise ServerError("Improperly configured filters for filtering")

    # apply filters
    for f in filters:
        query = f.apply_to_query(query=query, params=params)

    return query


# content/response encoding
CONTENT_ENCODING_JSON = "application/json"
CONTENT_ENCODING_XML = "application/xml"
CONTENT_ENCODING_MULTIPART = "multipart/form-data"


def _get_encoding_for_header(request: HttpRequest, header: str) -> str:
    """Extract header value from request and interpret it as encoding value
    :raises InvalidParamTypeError: In case header value is not of type string
    """
    # check param types
    if not isinstance(request, HttpRequest):
        raise InvalidParamTypeError("Invalid request instance datatype to determine encoding")
    if not isinstance(header, str):
        raise InvalidParamTypeError("Invalid header datatype to determine encoding")

    # extract header
    header = header.upper()
    header_value = request.META.get(header, "application/json")
    if not isinstance(header_value, str):
        raise InvalidParamTypeError("Invalid datatype of header value to determine encoding")

    header_value = header_value.lower()
    prefix_mapping = {
        "application/json": CONTENT_ENCODING_JSON,
        "application/xml": CONTENT_ENCODING_XML,
        "text/xml": CONTENT_ENCODING_XML,
        "multipart/form-data": CONTENT_ENCODING_MULTIPART,
    }
    result = header_value
    for key, value in prefix_mapping.items():
        if header_value.startswith(key):
            result = value
            break

    return result


def get_request_body_encoding(request: HttpRequest) -> str:
    """Extract request body encoding operating over Content-Type HTTP header"""
    return _get_encoding_for_header(request, "CONTENT_TYPE")


def get_request_accept_encoding(request: HttpRequest) -> str:
    """Extract request accept encoding operating over Http-Accept HTTP header"""
    return _get_encoding_for_header(request, "HTTP_ACCEPT")


def get_current_request() -> LambRequest | None:
    return LambGRequestMiddleware.get_request(None)


# datetime
def datetime_end(value: date | datetime) -> datetime:
    if not isinstance(value, (date | datetime)):
        raise InvalidParamTypeError("Invalid data type for date/datetime convert")

    return datetime(
        year=value.year,
        month=value.month,
        day=value.day,
        hour=23,
        minute=59,
        second=59,
        microsecond=999,
        tzinfo=getattr(value, "tzinfo", None),
    )


def datetime_begin(value: date | datetime) -> datetime:
    if not isinstance(value, (date | datetime)):
        raise InvalidParamTypeError("Invalid data type for date/datetime convert")

    return datetime(
        year=value.year,
        month=value.month,
        day=value.day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=getattr(value, "tzinfo", None),
    )


# other


def get_settings_value(*names, req_type: Callable | None = None, allow_none: bool = True, **kwargs):
    if len(names) == 0:
        raise InvalidParamValueError("At least one setting name required")
    elif len(names) == 1:
        names_msg = names[0]
    else:
        names_msg = f"{names[0]} ({'/'.join(names[1:])})"

    # check deprecations
    if len(names) > 1:
        target_setting_name = names[0]
        for name in names[1:]:
            try:
                _ = dpath_value(settings, key_path=name, req_type=req_type, allow_none=allow_none, **kwargs)
                warnings.warn(
                    f"Usage of deprecated settings name discovered {name}, use {target_setting_name} instead. "
                    f"If default or explicit value exist - value under {name} would be ignored",
                    DeprecationWarning,
                    stacklevel=2,
                )
            except (ImportError, AttributeError, InvalidBodyStructureError):
                continue

    # extract value
    for index, name in enumerate(names):
        try:
            result = dpath_value(settings, key_path=name, req_type=req_type, allow_none=allow_none, **kwargs)
            if index > 0:
                warnings.warn(
                    f"Use of deprecated settings param {name}, use {names[0]} instead", DeprecationWarning, stacklevel=2
                )
            return result
        except (ImportError, AttributeError, InvalidBodyStructureError):
            continue
        except Exception as e:
            raise ImproperlyConfiguredError(
                f"Could not locate {names_msg} settings value with params:"
                f" req_type={req_type}, allow_none={allow_none}, kwargs={kwargs}"
            ) from e
    raise ImproperlyConfiguredError(f"Could not locate {names_msg} settings value")


def inject_app_defaults(application: str):
    """Inject an application's default settings"""
    try:
        __import__(f"{application}.settings")
        import sys

        # Import our defaults, project defaults, and project settings
        _app_settings = sys.modules[f"{application}.settings"]
        _def_settings = sys.modules["django.conf.global_settings"]
        _settings = sys.modules["django.conf"].settings

        # Add the values from the application.settings module
        for _k in dir(_app_settings):
            if _k.isupper():
                # Add the value to the default settings module
                setattr(_def_settings, _k, getattr(_app_settings, _k))

                # Add the value to the settings, if not already present
                if not hasattr(_settings, _k):
                    setattr(_settings, _k, getattr(_app_settings, _k))

        from lamb.utils.dpath import adapt_dict_impl

        adapt_dict_impl()
    except ImportError:
        # Silently skip failing settings modules
        pass


def check_device_info_versions_above(
    source: Any,
    versions: list[tuple[str, int]],
    default: bool,
    skip_options: bool = True,
) -> bool:
    """Application versions check function

    If request/device_info object have info about platform and app build will check compatibility of versions:
    - `default` value used in case of device_info version missing
    - for matched platforms compare app_build field and returns True/False depends on result
    """

    from lamb.types.device_info_type import DeviceInfo

    # prepare params
    if isinstance(source, HttpRequest):
        if skip_options and source.method == "OPTIONS":
            return True
        _source = getattr(source, "lamb_device_info", None)
    else:
        _source = source

    if not isinstance(_source, DeviceInfo | None.__class__):
        logger.warning(f"received object: {source, source.__class__}")
        raise ServerError("Invalid object received for version checking")

    # early return
    if source is None:
        return default
    if _source.app_build is None:
        return default
    if _source.device_platform is None:
        return default

    for min_v in versions:
        try:
            _platform = min_v[0].lower()
            _min_app_build = int(min_v[1]) if not isinstance(min_v[1], int | float) else min_v[1]
            if _source.device_platform.lower() == _platform and _min_app_build > _source.app_build:
                return False
        except Exception as e:
            logger.warning(f"Skip above version checking for {min_v} cause of invalid structure, error: {e}")
            continue

    return True


def humanize_bytes(num, suffix="b"):
    for unit in ("", "K", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"


BANK_CARDS_REGEX_MAPPING = {
    "VISA": re.compile(r"^4[0-9]{12}(?:[0-9]{3})?$"),
    "MASTER CARD": re.compile(r"^(?:5[1-5][0-9]{2}|222[1-9]|22[3-9][0-9]|2[3-6][0-9]{2}|27[01][0-9]|2720)[0-9]{12}$"),
    "AMERICAN EXPRESS": re.compile(r"^3[47][0-9]{13}$"),
    "JCB": re.compile(r"^(?:2131|1800|35\d{3})\d{11}$"),
    "DINERS CLUB": re.compile(r"^3(?:0[0-5]|[68][0-9])[0-9]{11}$"),
    "DISCOVER": re.compile(r"^6(?:011|5[0-9]{2})[0-9]{12}$"),
    "MIR": re.compile(r"^220[0-4][0-9]{12}$"),
}


def bank_card_type_parse(masked_pan: str) -> str | None:
    # replace masking symbols
    _pan = masked_pan
    _pan = _pan.replace("-", "")
    _pan = _pan.replace(" ", "")
    _pan = _pan.replace("X", "*")

    # padding from last unknown symbol
    if len(_pan) < 16 and "*" in _pan:
        last_index = _pan.rindex("*")
        _pan = _pan[:last_index] + "*" * (16 - len(_pan)) + _pan[last_index:]

    # finally replace
    _pan = _pan.replace("*", "0")
    card_type = None
    for result, regex in BANK_CARDS_REGEX_MAPPING.items():
        if regex.match(_pan) is not None:
            card_type = result
            break

    return card_type


# time cached
_timed_lru_cache_functions: dict[Callable, Callable] = {}


def timed_lru_cache(**timedelta_kwargs):
    def _wrapper(func):
        update_delta = timedelta(**timedelta_kwargs)
        next_update = datetime.now(tz=TZ_UTC) + update_delta
        func_full_name = f"{sys.modules[func.__module__].__name__}.{func.__name__}"
        logger.debug(f"timed_lru_cache initial update calculated: {func_full_name} -> {next_update}")
        # Apply @lru_cache to func with no cache size limit
        func_lru_cached = functools.lru_cache(None)(func)

        _timed_lru_cache_functions[func] = func_lru_cached
        logger.debug(f"time cached functions: {_timed_lru_cache_functions}")

        @functools.wraps(func_lru_cached)
        def _wrapped(*args, **kwargs):
            nonlocal next_update
            now = datetime.now(tz=TZ_UTC)
            if now >= next_update:
                func_lru_cached.cache_clear()
                next_update = now + update_delta
                logger.debug(f"timed_lru_cache next update calculated: {func_full_name} -> {next_update}")
            return func_lru_cached(*args, **kwargs)

        return _wrapped

    return _wrapper


def timed_lru_cache_clear():
    for _func, wrapped_func in _timed_lru_cache_functions.items():
        wrapped_func.cache_clear()
        logger.warning(f"time_lru_cache cleared for: {_func} -> {wrapped_func}")


# async downloads
@enum.unique
class AsyncFallStrategy(str, enum.Enum):
    RAISING = "RAISING"
    NONE = "NONE"
    EXCEPTION = "EXCEPTION"


def _handle_async_fall(e: Exception, fall_strategy: AsyncFallStrategy):
    if fall_strategy == AsyncFallStrategy.RAISING:
        raise e
    elif fall_strategy == AsyncFallStrategy.NONE:
        return None
    elif fall_strategy == AsyncFallStrategy.EXCEPTION:
        return e
    else:
        logger.warning(f"Invalid strategy received: {fall_strategy}")
        raise ServerError("Invalid async fall strategy mode")


@sync_to_async
def _async_request_url(
    url: str | None, timeout, fall_strategy: AsyncFallStrategy, headers: dict[str, Any] | None = None
) -> requests.Response | Exception | None:
    logger.debug(f"downloading resource from url: {url}, timeout={timeout}, headers={headers}")
    if url is None:
        return None
    else:
        try:
            headers = headers or {}
            res = requests.get(url, timeout=timeout, headers=headers)
            if res.status_code != 200:
                raise ExternalServiceError(f"Could not download resource, invalid status: {url}")
            return res
        except Exception as e:
            return _handle_async_fall(e, fall_strategy)


async def _async_request_resources(
    urls: list[str | None], timeout: int, fall_strategy: AsyncFallStrategy, headers: dict[str, Any] | None = None
) -> list[requests.Response | Exception | None]:
    tasks = []
    for url in urls:
        tasks.append(_async_request_url(url=url, timeout=timeout, headers=headers, fall_strategy=fall_strategy))
    result = await asyncio.gather(*tasks)

    return result


def async_request_urls(
    urls: list[str | None],
    timeout=30,
    headers: dict[str, Any] | None = None,
    fall_strategy: AsyncFallStrategy = AsyncFallStrategy.RAISING,
) -> list[requests.Response | Exception | None]:
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _async_request_resources(urls=urls, timeout=timeout, headers=headers, fall_strategy=fall_strategy)
        )
    finally:
        loop.close()
    return result


def async_download_resources(
    urls: list[str | None],
    timeout=30,
    headers: dict[str, Any] | None = None,
    fall_strategy: AsyncFallStrategy = AsyncFallStrategy.RAISING,
) -> list[bytes | None]:
    result = async_request_urls(urls=urls, timeout=timeout, headers=headers, fall_strategy=fall_strategy)
    result = [res.content if isinstance(res, requests.Response) else res for res in result]
    return result


def async_download_images(
    urls: list[str | None],
    timeout=30,
    headers: dict[str, Any] | None = None,
    fall_strategy: AsyncFallStrategy = AsyncFallStrategy.RAISING,
) -> list[PILImage.Image | None]:
    result = async_download_resources(urls=urls, timeout=timeout, headers=headers, fall_strategy=fall_strategy)
    buffer = []
    for res in result:
        try:
            if res is None:
                buffer.append(None)
                continue
            buffer.append(PILImage.open(io.BytesIO(res)))
        except Exception as e:
            buffer.append(_handle_async_fall(e, fall_strategy))
    return buffer


def str_coercible(cls):
    def __str__(self):
        return self.__unicode__()

    cls.__str__ = __str__
    return cls


def get_columns(mixed):
    """
    Return a collection of all Column objects for given SQLAlchemy
    object.

    The type of the collection depends on the type of the object to return the
    columns from.

    :param mixed:
        SA Table object, SA Mapper, SA declarative class, SA declarative class
        instance or an alias of any of these objects
    """
    if isinstance(mixed, sqlalchemy.sql.selectable.Selectable):
        try:
            return mixed.selected_columns
        except AttributeError:  # SQLAlchemy <1.4
            return mixed.c
    if isinstance(mixed, sqlalchemy.orm.util.AliasedClass):
        return sqlalchemy.inspect(mixed).mapper.columns
    if isinstance(mixed, sqlalchemy.orm.Mapper):
        return mixed.columns
    if isinstance(mixed, InstrumentedAttribute):
        return mixed.property.columns
    if isinstance(mixed, ColumnProperty):
        return mixed.columns
    if isinstance(mixed, sqlalchemy.Column):
        return [mixed]
    if not isclass(mixed):
        mixed = mixed.__class__
    return sqlalchemy.inspect(mixed).columns


def get_primary_keys(mixed):
    """
    Return an OrderedDict of all primary keys for given Table object,
    declarative class or declarative class instance.

    :param mixed:
        SA Table object, SA declarative class or SA declarative class instance
    """
    return OrderedDict(((key, column) for key, column in get_columns(mixed).items() if column.primary_key))


# image utils
def image_convert_to_rgb(image: PILImage.Image) -> PILImage.Image:
    if image.mode == "RGBA":
        image.load()
        background = PILImage.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])
        return background
    else:
        return image.convert("RGB")


def file_is_svg(file: str | BinaryIO) -> bool:
    try:
        tag = next(cElementTree.iterparse(file, ("start",)))[1].tag
    except cElementTree.ParseError:
        return False

    return tag == "{http://www.w3.org/2000/svg}svg"


def image_decode_base64(b64image: str, verify: bool = False) -> PILImage:
    img_bytes = base64.b64decode(b64image)

    buffer = io.BytesIO(img_bytes)
    image = PILImage.open(buffer)
    if verify:
        image.verify()
        image = PILImage.open(buffer)  # verify requires to re
    return image


def get_file_mime_type(src_file: str | bytes | UploadedFile) -> str:
    import magic

    try:
        if isinstance(src_file, UploadedFile):
            with tempfile.NamedTemporaryFile() as dst:
                for chunk in src_file.chunks():
                    dst.write(chunk)
                dst.seek(0)
                buffer = dst.read()
                src_file.seek(0)
        elif isinstance(src_file, str):
            with open(src_file, "rb") as src:
                buffer = src.read()
        elif isinstance(src_file, PILImage.Image):
            buffer = io.BytesIO()
            src_file.save(buffer, format=src_file.format)
            buffer = buffer.getvalue()
        elif isinstance(src_file, bytes):
            buffer = src_file
        else:
            logger.warning(
                f"Could not determine mime-type cause of invalid object: {src_file} of class {src_file.__class__}"
            )
            raise ServerError("Could not determine mime-type cause of invalid object")

        # determine mime-type
        mime_type = magic.Magic(mime=True).from_buffer(buffer)
        mime_type = mime_type.lower()
        return mime_type
    except ApiError:
        raise
    except Exception as e:
        raise InvalidParamTypeError("Could not detect mime-type of uploaded file") from e


# timezones
TZ_MSK = zoneinfo.ZoneInfo("Europe/Moscow")
TZ_UTC = UTC


def tz_now() -> datetime:
    return d_timezone.now().astimezone(TZ_UTC)
