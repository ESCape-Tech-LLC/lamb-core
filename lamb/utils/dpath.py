from __future__ import annotations

import contextlib
import copy
import logging
import os
from collections.abc import Callable, Mapping
from functools import reduce
from operator import getitem
from typing import Any

import dpath
from django.conf import Settings
from django.http.request import QueryDict
from lxml import etree
from lxml.etree import _Element as EtreeElement
from lxml.etree import _ElementTree as Etree

from lamb import exc
from lamb.ext.lxml import __lxml_hints_reverse_map__

logger = logging.getLogger(__name__)

__all__ = ["adapt_dict_impl", "dpath_value"]


DictObject = dict | EtreeElement | Etree | Mapping | Settings
KeyPath = str | list[Any] | tuple[Any]

# main
# TODO: migrate functions to cython with pure python versions - could be much faster
_UNSET = object()


class _MissingPath(IndexError):
    """Carry the source-specific error for an unresolved path."""

    def __init__(self, error: exc.InvalidBodyStructureError):
        super().__init__(error.message)
        self.error = error


def dpath_value(
    dict_object: DictObject | None = None,
    key_path: KeyPath | None = None,
    req_type: Callable | None = None,
    allow_none: bool = False,
    transform: Callable | None = None,
    *,
    default_on_missing: Any = _UNSET,
    missing_error: Callable[[], Exception] | None = None,
    invalid_error: Callable[[], Exception] | None = None,
    strict: bool = False,
    **kwargs,
):
    """Search for object in provided dict_object under key_path

    :param dict_object: Container to find data within
    :param key_path: Query string
    :param req_type: Type of argument that expected
    :param allow_none: Return None without exception if leaf exist and equal to None
    :param transform: Optional callback (lamb.utils.transformers function or other)
        to apply on extracted value before return

    :param default_on_missing: Return this value unchanged when the path cannot be found.
    :param missing_error: Exception class or zero-argument factory for an unresolved path.
        Mutually exclusive with default_on_missing.
    :param invalid_error: Exception class or zero-argument factory for a disallowed None,
        conversion failure, or validation error in transform (ValueError or a Lamb
        parameter/structure error).
    :param strict: Require the exact req_type before transform instead of coercing the value.
    :param kwargs: Source-specific options and the legacy fallback `default`, which also
        covers conversion and transformation failures. Use it separately from the new
        missing/invalid policies.

    :return: Extracted value

    """

    if default_on_missing is not _UNSET and missing_error is not None:
        raise exc.ProgrammingError("default_on_missing and missing_error are mutually exclusive")
    if "default" in kwargs and (
        default_on_missing is not _UNSET or missing_error is not None or invalid_error is not None
    ):
        raise exc.ProgrammingError("default cannot be combined with default_on_missing, missing_error or invalid_error")
    if strict and not isinstance(req_type, type):
        raise exc.ProgrammingError("strict=True requires a type for req_type")

    def handle_error(error: Exception):
        if "default" in kwargs:
            return kwargs["default"]
        if isinstance(error, exc.ApiError):
            raise error
        raise exc.ServerError("Failed to parse params due unknown error") from error

    # prepare key_path
    if not isinstance(key_path, (str, list, tuple)):
        raise exc.ServerError

    _key_path = copy.copy(key_path)

    # query
    try:
        if type(dict_object) is dict and type(key_path) is str and _impl_dict is _impl_dict_reduce:
            # A flat JSON key is literal in the reduce engine. Return missing defaults before conversion.
            try:
                if (default_on_missing is not _UNSET or "default" in kwargs) and key_path not in dict_object:
                    return kwargs.get("default", default_on_missing)
                result = dict_object[key_path]
            except Exception as error:
                raise IndexError("Path not exist") from error
        elif isinstance(dict_object, os._Environ):
            result = _impl_environ(dict_object, key_path=_key_path, **kwargs)
        elif isinstance(dict_object, dict):
            result = _impl_dict(dict_object, key_path=_key_path, **kwargs)
        elif isinstance(dict_object, Settings):
            result = _impl_django_conf(dict_object, key_path=_key_path, **kwargs)
        elif isinstance(dict_object, QueryDict):
            result = _impl_query_dict(dict_object, key_path=_key_path, **kwargs)
        elif isinstance(dict_object, Etree | EtreeElement):
            result = _impl_etree(dict_object, key_path=_key_path, **kwargs)
        else:
            result = _impl_dict(dict_object, key_path=_key_path, **kwargs)
    except IndexError as lookup_error:
        if default_on_missing is not _UNSET:
            return default_on_missing
        if "default" in kwargs:
            return kwargs["default"]
        if missing_error is not None:
            raise missing_error() from lookup_error
        if isinstance(lookup_error, _MissingPath):
            raise lookup_error.error from lookup_error.__cause__
        raise exc.InvalidBodyStructureError(f"Could not locate key: {key_path}") from lookup_error
    except Exception as error:
        return handle_error(error)

    try:
        # check for none
        if result is None:
            if allow_none:
                return None
            raise exc.InvalidParamTypeError(
                f"Invalid data type for param: {key_path}", error_details={"key_path": key_path}
            )

        if req_type is not None and type(result) is not req_type:
            message = f"Invalid data type for param '{key_path}'"
            if strict:
                raise exc.InvalidParamTypeError(message, error_details={"key_path": key_path})
            try:
                result = req_type(result)
            except (ValueError, TypeError) as error:
                raise exc.InvalidParamTypeError(message, error_details={"key_path": key_path}) from error

        return transform(result) if transform is not None else result
    except Exception as error:
        if invalid_error is not None and isinstance(
            error, (exc.InvalidParamTypeError, exc.InvalidParamValueError, exc.InvalidBodyStructureError, ValueError)
        ):
            raise invalid_error() from error
        return handle_error(error)


# dict engine utils
def _impl_dict_dpath(dict_object: dict[Any, Any], key_path: KeyPath, **_) -> Any:
    items: list[Any] = dpath.values(dict_object, key_path)
    result = items[0]
    return result


def _impl_dict_reduce(dict_object: dict[Any, Any], key_path: KeyPath, **_) -> Any:
    # TODO: candidate to remove - traverse speed same
    try:
        if isinstance(key_path, str):
            key_path = [key_path]
        return reduce(getitem, key_path, dict_object)
    except Exception as e:
        raise IndexError("Path not exist") from e


# dpath_value could be used before full django and settings init complete
# so until init finished use stable dpath version
_impl_dict = _impl_dict_reduce


def adapt_dict_impl():
    from django.conf import settings

    engine_value = dpath_value(settings, "LAMB_DPATH_DICT_ENGINE", str, default=None)

    global _impl_dict
    logger.debug(f"dpath_value settings value is: {engine_value}")
    if engine_value is None or engine_value == "dpath":
        _impl_dict = _impl_dict_dpath
        logger.debug("dpath_value: impl adapted - dpath")
    elif engine_value == "reduce":
        _impl_dict = _impl_dict_reduce
        logger.debug("dpath_value: impl adapted - reduce")
    else:
        raise exc.ImproperlyConfiguredError(f"Unknown dict dpath implementation: {settings.LAMB_DPATH_DICT_ENGINE}")


# other sources
def _impl_etree(element: EtreeElement | Etree, key_path: str, namespaces: dict | None = None, **_) -> Any:
    """Etree/EtreeElement implementation

    :param element: Element object to extract value
    :param key_path: Subtag name
    :param namespaces: Namespaces for XML find mapping
    :return: Extracted value
    """
    if not isinstance(element, EtreeElement | Etree):
        logger.warning(f"Improperly configured element param data type: {element}")
        raise exc.InvalidParamTypeError("ArgParsing. Improperly configured param source")
    if not isinstance(key_path, str):
        logger.warning(f"Improperly configured key_path param data type: {key_path}")
        raise exc.InvalidParamTypeError("ArgParsing. Improperly configured param search key_path")

    try:
        # extract child and text
        child = element.find(key_path, namespaces=namespaces)
        if child is None:
            raise _MissingPath(
                exc.InvalidBodyStructureError(
                    f"Could not extract param for key_path {key_path} from provided XML data",
                    error_details={"key_path": key_path},
                )
            )
        result = child.text

        # try auto-discover data type
        if result is not None:
            # validate result type through typeHint detecting in key_path and converting to ot
            hinted_type = child.get("typeHint")
            if hinted_type is not None and hinted_type in __lxml_hints_reverse_map__:
                with contextlib.suppress(Exception):
                    result = __lxml_hints_reverse_map__[hinted_type](result)

        return result
    except exc.ApiError, _MissingPath:
        raise
    except etree.ParseError as e:
        raise exc.InvalidBodyStructureError(
            f"Could not extract param for key_path {key_path} from provided XML data",
            error_details={"key_path": key_path},
        ) from e
    except Exception as e:
        raise exc.ServerError(
            "Etree subtag query. Could not locate extract value with some unhandled exception."
        ) from e


def _impl_django_conf(settings: Settings, key_path: KeyPath, **_r) -> Any:
    """
    Implementation to query and parse djnago configs
    :param settings: Initialized Settings object
    :param key_path: Variable name
    :return: Extracted value
    """
    try:
        if not isinstance(key_path, str):
            raise exc.ServerError
        # key_path = ".".join(key_path)
        result = getattr(settings, key_path)  # type: Any
        return result
    except Exception as e:
        error = exc.InvalidBodyStructureError(
            f"Could not locate field for key_path = {key_path} from settings object",
            error_details={"key_path": key_path},
        )
        if isinstance(e, AttributeError):
            raise _MissingPath(error) from e
        raise error from e


def _impl_query_dict(dict_object: QueryDict, key_path: str | list[str] | None = None, **kwargs) -> Any:
    # TODO: support for multiple values
    return _impl_dict(dict_object.dict(), key_path, **kwargs)


def _impl_environ(env: os._Environ, key_path: str | list[str] | None = None, **kwargs) -> Any:
    if not isinstance(key_path, str):
        raise exc.ProgrammingError("Environment variable name must be a string")

    if key_path.endswith("_FILE"):
        # early return - seems not like patch required
        return _impl_dict(dict_object=env, key_path=key_path, **kwargs)

    key_path_secret = key_path + "_FILE"
    if key_path not in env and key_path_secret in env:
        try:
            file_path = env[key_path_secret]
            with open(file_path) as f:
                result = f.read().strip()
                env[key_path] = result
                logger.warning(f"env variable monkey patching from _FILE version: {key_path} << {key_path_secret}")
        except Exception as e:
            raise exc.InvalidBodyStructureError("Could not adapt _FILE like env variable") from e

    return _impl_dict(dict_object=env, key_path=key_path, **kwargs)
