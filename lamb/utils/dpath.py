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
# TODO: modify - split logic of default for presented and not exist key_path


def dpath_value(
    dict_object: DictObject | None = None,
    key_path: KeyPath | None = None,
    req_type: Callable | None = None,
    allow_none: bool = False,
    transform: Callable | None = None,
    **kwargs,
):
    """Extract a value from a nested data structure using a key path.

    This function provides a unified interface for extracting values from various
    data sources including dictionaries, XML elements, Django settings, environment
    variables, and QueryDict objects. It supports type conversion, validation,
    and transformation of the extracted values.

    Args:
        dict_object: The container to search within. Can be a dict, XML element,
            Django settings, environment variables, or QueryDict.
        key_path: The path to the desired value. Can be a string, list, or tuple.
            For nested structures, use a list or tuple of keys/indices.
        req_type: Optional type to convert the extracted value to. If conversion
            fails, raises InvalidParamTypeError.
        allow_none: If True, returns None when the extracted value is None.
            If False (default), raises InvalidParamTypeError for None values.
        transform: Optional callable to transform the extracted value before
            returning. Useful for validation or custom parsing.
        **kwargs: Additional keyword arguments:
            - default: Value to return if the key_path is not found
            - Other arguments are passed to the transformer function

    Returns:
        The extracted value, potentially transformed and/or type-converted.

    Raises:
        InvalidParamTypeError: If the value is None and allow_none=False, or
            if type conversion fails.
        InvalidBodyStructureError: If the key_path cannot be found.
        ServerError: For other unexpected errors during extraction.

    Examples:
        # Simple dictionary access
        data = {"user": {"name": "John", "age": "30"}}
        name = dpath_value(data, ["user", "name"])  # Returns "John"
        age = dpath_value(data, ["user", "age"], int)  # Returns 30 (int)

        # With default value
        city = dpath_value(data, ["user", "city"], default="Unknown")

        # With transformation
        from functools import partial
        from lamb.utils import transformers
        date_val = dpath_value(
            data,
            "birth_date",
            transform=partial(transformers.transform_date, __format="%Y-%m-%d")
        )

        # Environment variable access
        import os
        debug_mode = dpath_value(os.environ, "DEBUG_MODE", bool, default=False)
    """

    # utils
    def _type_convert(_result):
        if type(_result) is req_type:
            return _result
        try:
            _result = req_type(_result)
            return _result
        except (ValueError, TypeError) as _e:
            raise exc.InvalidParamTypeError(
                f"Invalid data type for param '{key_path}'", error_details={"key_path": key_path}
            ) from _e

    # prepare key_path
    if not isinstance(key_path, str | list | tuple):
        raise exc.ServerError

    _key_path = copy.copy(key_path)

    # query
    try:
        # custom dispatch
        try:
            if isinstance(dict_object, os._Environ):
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
                # last mile - attempt as dict
                result = _impl_dict(dict_object, key_path=_key_path, **kwargs)
        except IndexError as e:
            raise exc.InvalidBodyStructureError(f"Could not locate key: {key_path}") from e

        # check for none
        if result is None:
            if allow_none:
                return None
            else:
                raise exc.InvalidParamTypeError(
                    f"Invalid data type for param: {key_path}", error_details={"key_path": key_path}
                )

        # apply type convert
        if req_type is not None:
            result = _type_convert(result)

        # apply transform
        if transform is not None:
            return transform(result)

        return result
    except Exception as e:
        if "default" in kwargs:
            return kwargs["default"]
        elif isinstance(e, exc.ApiError):
            raise
        else:
            raise exc.ServerError("Failed to parse params due unknown error") from e


# dict engine utils
def _impl_dict_dpath(dict_object: dict[Any, Any], key_path: KeyPath, **_) -> Any:
    """Extract value from dictionary using dpath library.

    Args:
        dict_object: Dictionary to search within
        key_path: Path to the desired value

    Returns:
        The extracted value

    Raises:
        IndexError: If the key_path cannot be found
    """
    items: list[Any] = dpath.values(dict_object, key_path)
    result = items[0]
    return result


def _impl_dict_reduce(dict_object: dict[Any, Any], key_path: KeyPath, **_) -> Any:
    """Extract value from dictionary using functools.reduce.

    Args:
        dict_object: Dictionary to search within
        key_path: Path to the desired value (must be list/tuple for this implementation)

    Returns:
        The extracted value

    Raises:
        IndexError: If the key_path cannot be found
    """
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
    """Adapt the dictionary implementation based on Django settings.

    This function reads the LAMB_DPATH_DICT_ENGINE setting from Django configuration
    and sets the appropriate implementation for dictionary value extraction.

    The setting can be:
        - "dpath" (default): Use the dpath library implementation
        - "reduce": Use the functools.reduce implementation

    If the setting is not configured or invalid, it defaults to "dpath".

    Raises:
        ImproperlyConfiguredError: If an unknown engine is specified in settings
    """
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
    """Extract value from XML element tree.

    Args:
        element: XML element or element tree to search within
        key_path: XPath expression to locate the desired element
        namespaces: Optional namespace mappings for XPath resolution

    Returns:
        The text content of the located element, potentially type-converted
        based on type hints in the XML

    Raises:
        InvalidParamTypeError: If element or key_path types are incorrect
        InvalidBodyStructureError: If the element cannot be found
        ServerError: For other unexpected errors
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
            raise exc.InvalidBodyStructureError(
                f"Could not extract param for key_path {key_path} from provided XML data",
                error_details={"key_path": key_path},
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
    except exc.ApiError:
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
    """Extract value from Django settings.

    Args:
        settings: Django settings object
        key_path: Name of the setting to retrieve (must be a string)

    Returns:
        The value of the specified setting

    Raises:
        InvalidBodyStructureError: If the setting cannot be found
        ServerError: If key_path is not a string
    """
    try:
        if not isinstance(key_path, str):
            raise exc.ServerError
        # key_path = ".".join(key_path)
        result = getattr(settings, key_path)  # type: Any
        return result
    except Exception as e:
        raise exc.InvalidBodyStructureError(
            f"Could not locate field for key_path = {key_path} from settings object",
            error_details={"key_path": key_path},
        ) from e


def _impl_query_dict(dict_object: QueryDict, key_path: str | list[str] | None = None, **kwargs) -> Any:
    """Extract value from Django QueryDict.

    Args:
        dict_object: QueryDict to search within
        key_path: Key to look up (passed to dict implementation)
        **kwargs: Additional arguments passed to dict implementation

    Returns:
        The extracted value
    """
    # TODO: support for multiple values
    return _impl_dict(dict_object.dict(), key_path, **kwargs)


def _impl_environ(env: os._Environ, key_path: str | list[str] | None = None, **kwargs) -> Any:
    """Extract value from environment variables.

    This implementation supports Docker secrets pattern where a secret value
    can be provided through a file referenced by an environment variable with
    the same name plus '_FILE' suffix.

    Args:
        env: Environment variables dictionary
        key_path: Name of the environment variable to retrieve (must be a string)
        **kwargs: Additional arguments passed to dict implementation

    Returns:
        The value of the environment variable, potentially loaded from a file

    Raises:
        ProgrammingError: If key_path is not a string
        InvalidBodyStructureError: If file-based environment variable cannot be loaded
    """
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
