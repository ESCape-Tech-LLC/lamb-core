from __future__ import annotations

import logging
from typing import Any, List, Union, Mapping, Callable, Optional
from operator import getitem
from functools import reduce, singledispatch

from django.conf import Settings
from django.http.request import QueryDict

# Lamb Framework
from lamb import exc
from lamb.ext.lxml import __lxml_hints_reverse_map__

# import dpath.util
import dpath
import jmespath
import jmespath.exceptions
from lxml.etree import _Element as EtreeElement
from lxml.etree import _ElementTree as Etree

logger = logging.getLogger(__name__)

__all__ = ["dpath_value", "adapt_dict_impl"]


# TODO: modify - split logic of default for presented and not exist key_path
# TODO: prepare good unit tests to check both dpath/jmespath implementations
# TODO: adapt implementations to unify syntax between implementations (lists, dot, slash - ['a', 'b'], 'a.b', 'a/b')
# TODO: check for proper support of implementations specific patterns like @ or list slices


def dpath_value(
    dict_object: Union[Optional[dict], EtreeElement, Etree, Mapping] = None,
    key_path: Union[str, List[str]] = None,
    req_type: Optional[Callable] = None,
    allow_none: bool = False,
    transform: Optional[Callable] = None,
    **kwargs,
):
    """Search for object in Dict or XML document

    :param dict_object: Document (Dict or _ElementTree or _Element) to find data
    :param key_path: Query string
    :param req_type: Type of argument that expected
    :param allow_none: Return None without exception if leaf exist and equal to None
    :param transform: Optional callback (labm.utils.transformers function or other)
        to apply on extracted value before return

    :param kwargs: Optional parameters:
        - `default` - default value is passed to extractor function
        - others - passed to the transformer (if set).

    :return: Extracted value

    """

    # utils
    def _type_convert(_result):
        if req_type is None:
            return _result
        # NOTE: disabled for explicit convert - for example in case of bool as int request
        # TODO: re-enable - faster
        # if isinstance(_result, req_type):
        #     return _result
        try:
            _result = req_type(_result)
            return _result
        except (ValueError, TypeError) as _e:
            raise exc.InvalidParamTypeError(
                "Invalid data type for param %s" % key_path, error_details={"key_path": key_path}
            ) from _e

    # query
    try:
        # get internal result
        result = _dpath_find_impl(dict_object, key_path=key_path, **kwargs)

        # check for none
        if result is None:
            if allow_none:
                return None
            else:
                raise exc.InvalidParamTypeError(
                    "Invalid data type for param %s" % key_path, error_details={"key_path": key_path}
                )

        # apply type convert
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
def _dict_engine_impl_dpath(dict_object: Optional[dict] = None, key_path: Union[str, List[str]] = None, **_) -> Any:
    items: List[Any] = dpath.values(dict_object, key_path)
    # items = dpath.util.values(dict_object, key_path)  # type: # List[Any]
    result = items[0]
    return result


def _dict_engine_impl_jmespath(dict_object: Optional[dict] = None, key_path: Union[str, List[str]] = None, **_) -> Any:
    # old version
    # if isinstance(key_path, list):
    #     key_path = ".".join(key_path)
    # items = jmespath.search(key_path, dict_object)  # type: Any
    # return items

    # new version
    if isinstance(key_path, list):
        _expr = ".".join(key_path)
        _exist_root = ".".join(["@"] + key_path[:-1])
        _exist_expr = key_path[-1]
    else:
        _expr = key_path
        _exist_root = "@"
        _exist_expr = key_path

    items = jmespath.search(_expr, dict_object)  # type: Any
    if items is None:
        # jmespath produce None in both case:
        # - field value is None
        # - field not exist
        try:
            exist = jmespath.search(
                f"contains(keys({_exist_root}), '{_exist_expr}')",
                dict_object,
            )
            if not exist:
                raise IndexError("Path not exist")
        except jmespath.exceptions.JMESPathTypeError as e:
            raise IndexError("Path not exist") from e

    return items


def _dict_engine_impl_traverse(dict_object: Optional[dict] = None, key_path: Union[str, List[str]] = None, **_) -> Any:
    # dumb - but fast
    try:
        if not isinstance(key_path, list):
            key_path = [key_path]

        result = dict_object
        while len(key_path) > 0:
            result = result[key_path.pop(0)]

        return result
    except Exception:
        raise IndexError("Path not exist")


def _dict_engine_impl_reduce(dict_object: Optional[dict] = None, key_path: Union[str, List[str]] = None, **_) -> Any:
    # TODO: candidate to remove - traverse speed same
    try:
        if isinstance(key_path, str):
            key_path = [key_path]
        return reduce(getitem, key_path, dict_object)
    except Exception:
        raise IndexError("Path not exist")


# dpath_value could be used before full django and settings init complete
# so until init finished use stable dpath version
_dict_impl = _dict_engine_impl_dpath


def adapt_dict_impl():
    from django.conf import settings

    engine_value = dpath_value(settings, "LAMB_DPATH_DICT_ENGINE", str, default=None)

    global _dict_impl
    logger.debug(f"dpath_value settings value is: {engine_value}")
    if engine_value is None or engine_value == "dpath":
        _dict_impl = _dict_engine_impl_dpath
        logger.debug("dpath_value: impl adapted - dpath")
    elif engine_value == "jmespath":
        _dict_impl = _dict_engine_impl_jmespath
        logger.debug("dpath_value: impl adapted - jmespath")
    elif engine_value == "traverse":
        _dict_impl = _dict_engine_impl_traverse
        logger.debug("dpath_value: impl adapted - traverse")
    elif engine_value == "reduce":
        _dict_impl = _dict_engine_impl_reduce
        logger.debug("dpath_value: impl adapted - reduce")
    else:
        raise exc.ImproperlyConfiguredError(f"Unknown dict dpath implementation: {settings.LAMB_DPATH_DICT_ENGINE}")


@singledispatch
def _dpath_find_impl(dict_object: Optional[dict] = None, key_path: Union[str, List[str]] = None, **_) -> Any:
    """
    Implementation for dict
    :param dict_object: Dict to find data
    :param key_path: Query string
    :return: Extracted value
    """

    try:
        return _dict_impl(dict_object=dict_object, key_path=key_path)
    except IndexError as e:
        raise exc.InvalidBodyStructureError(
            "Could not locate field for key_path %s from provided dict data" % key_path,
            error_details={"key_path": key_path},
        ) from e
    except AttributeError as e:
        raise exc.ServerError("Invalid key_path type for querying in dict", error_details={"key_path": key_path}) from e


@_dpath_find_impl.register(EtreeElement)
@_dpath_find_impl.register(Etree)
def _etree_find_impl(element: Union[EtreeElement, Etree], key_path: str, namespaces: Optional[dict] = None, **_) -> Any:
    """
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
    except Etree.ParseError as e:
        raise exc.InvalidBodyStructureError(
            "Could not extract param for key_path %s from provided XML data" % key_path,
            error_details={"key_path": key_path},
        ) from e
    except Exception as e:
        raise exc.ServerError(
            "Etree subtag query. Could not locate extract value with some unhandled exception."
        ) from e


@_dpath_find_impl.register(Settings)
def _django_conf_impl(settings: Settings, key_path: str, **_r) -> Any:
    """
    Implementation to query and parse djnago configs
    :param settings: Initialized Settings object
    :param key_path: Variable name
    :return: Extracted value
    """
    try:
        result = getattr(settings, key_path)  # type: Any
        return result
    except Exception as e:
        raise exc.InvalidBodyStructureError(
            f"Could not locate field for key_path = {key_path} from settings object",
            error_details={"key_path": key_path},
        ) from e


@_dpath_find_impl.register(QueryDict)
def _django_query_dict_impl(dict_object: QueryDict, key_path: Union[str, List[str]] = None, **kwargs) -> Any:
    # TODO: support for multiple values
    return _dpath_find_impl(dict_object.dict(), key_path, **kwargs)
