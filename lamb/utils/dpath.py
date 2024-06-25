from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Tuple, Union, Mapping, Callable, Optional
from operator import getitem
from functools import reduce

from django.conf import Settings
from django.http.request import QueryDict

# Lamb Framework
from lamb import exc
from lamb.ext.lxml import __lxml_hints_reverse_map__

# import dpath.util
import dpath
import lxml.etree as etree
from lxml.etree import _Element as EtreeElement
from lxml.etree import _ElementTree as Etree

logger = logging.getLogger(__name__)

__all__ = ["dpath_value", "adapt_dict_impl"]


DictObject = Union[dict, EtreeElement, Etree, Mapping, Settings]
KeyPath = Union[str, List[Any], Tuple[Any]]

# main
# TODO: migrate functions to cython with pure python versions - could be much faster
# TODO: modify - split logic of default for presented and not exist key_path


def dpath_value(
    dict_object: Optional[DictObject] = None,
    key_path: Optional[KeyPath] = None,
    req_type: Optional[Callable] = None,
    allow_none: bool = False,
    transform: Optional[Callable] = None,
    **kwargs,
):
    """Search for object in provided dict_object under key_path

    :param dict_object: Container to find data within
    :param key_path: Query string
    :param req_type: Type of argument that expected
    :param allow_none: Return None without exception if leaf exist and equal to None
    :param transform: Optional callback (lamb.utils.transformers function or other)
        to apply on extracted value before return

    :param kwargs: Optional parameters:
        - `default` - default value is passed to extractor function
        - others - passed to the transformer (if set).

    :return: Extracted value

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
    if not isinstance(key_path, (str, list, tuple)):
        raise exc.ServerError

    _key_path = copy.copy(key_path)

    # query
    try:
        # custom dispatch
        try:
            if isinstance(dict_object, dict):
                result = _impl_dict(dict_object, key_path=_key_path, **kwargs)
            elif isinstance(dict_object, Settings):
                result = _impl_django_conf(dict_object, key_path=_key_path, **kwargs)
            elif isinstance(dict_object, QueryDict):
                result = _impl_query_dict(dict_object, key_path=_key_path, **kwargs)
            elif isinstance(dict_object, (Etree, EtreeElement)):
                result = _impl_etree(dict_object, key_path=_key_path, **kwargs)
            else:
                # last mile - attempt as dict
                result = _impl_dict(dict_object, key_path=_key_path, **kwargs)
        except IndexError:
            raise exc.InvalidBodyStructureError(f"Could not locate key: {key_path}")

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
        if "default" in kwargs.keys():
            return kwargs["default"]
        elif isinstance(e, exc.ApiError):
            raise
        else:
            raise exc.ServerError("Failed to parse params due unknown error") from e


# dict engine utils
def _impl_dict_dpath(dict_object: Dict[Any, Any], key_path: KeyPath, **_) -> Any:
    items: List[Any] = dpath.values(dict_object, key_path)
    result = items[0]
    return result


def _impl_dict_reduce(dict_object: Dict[Any, Any], key_path: KeyPath, **_) -> Any:
    # TODO: candidate to remove - traverse speed same
    try:
        if isinstance(key_path, str):
            key_path = [key_path]
        return reduce(getitem, key_path, dict_object)
    except Exception:
        raise IndexError("Path not exist")


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
def _impl_etree(element: Union[EtreeElement, Etree], key_path: str, namespaces: Optional[dict] = None, **_) -> Any:
    """Etree/EtreeElement implementation

    :param element: Element object to extract value
    :param key_path: Subtag name
    :param namespaces: Namespaces for XML find mapping
    :return: Extracted value
    """
    if not isinstance(element, (EtreeElement, Etree)):
        logger.warning("Improperly configured element param data type: %s" % element)
        raise exc.InvalidParamTypeError("ArgParsing. Improperly configured param source")
    if not isinstance(key_path, str):
        logger.warning("Improperly configured key_path param data type: %s" % key_path)
        raise exc.InvalidParamTypeError("ArgParsing. Improperly configured param search key_path")

    try:
        # extract child and text
        child = element.find(key_path, namespaces=namespaces)
        if child is None:
            raise exc.InvalidBodyStructureError(
                "Could not extract param for key_path %s from provided XML data" % key_path,
                error_details={"key_path": key_path},
            )
        result = child.text

        # try auto-discover data type
        if result is not None:
            # validate result type through typeHint detecting in key_path and converting to ot
            hinted_type = child.get("typeHint")
            if hinted_type is not None and hinted_type in __lxml_hints_reverse_map__.keys():
                try:
                    result = __lxml_hints_reverse_map__[hinted_type](result)
                except Exception:
                    pass

        return result
    except exc.ApiError:
        raise
    except etree.ParseError as e:
        raise exc.InvalidBodyStructureError(
            "Could not extract param for key_path %s from provided XML data" % key_path,
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
        raise exc.InvalidBodyStructureError(
            f"Could not locate field for key_path = {key_path} from settings object",
            error_details={"key_path": key_path},
        ) from e


def _impl_query_dict(dict_object: QueryDict, key_path: Union[str, List[str]] = None, **kwargs) -> Any:
    # TODO: support for multiple values
    return _impl_dict(dict_object.dict(), key_path, **kwargs)
