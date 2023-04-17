from __future__ import annotations

import enum
import uuid
import logging
from typing import Optional
from datetime import date, datetime

# Lamb Framework
from lamb.exc import (
    ApiError,
    ServerError,
    InvalidParamTypeError,
    InvalidBodyStructureError,
)

from lxml.etree import _Element, tostring

logger = logging.getLogger(__name__)


__all__ = ["etree_as_string", "detect_lxml_type_hint"]


# utilities
def __add_numeric__(elem, item):
    elem.text = str(item)


def __add_boolean__(elem, item):
    if item:
        elem.text = "true"
    else:
        elem.text = "false"


def __add_enum__(elem, item):
    elem.text = str(item.value)


def __add_string__(elem, item):
    elem.text = item


def __add_datetime__(elem, item):
    elem.text = item.strftime("%Y-%m-%d %H:%M:%S")


def __add_date__(elem, item):
    elem.text = item.strftime("%Y-%m-%d")


def __add_none__(_, __):
    pass


def __add_uuid__(elem, item):
    elem.text = str(item)


__lxml_mapping__ = {
    int: (__add_numeric__, "integer"),
    float: (__add_numeric__, "float"),
    bool: (__add_boolean__, "boolean"),
    str: (__add_string__, "string"),
    datetime: (__add_datetime__, "string"),
    date: (__add_date__, "string"),
    enum.IntEnum: (__add_enum__, "integer"),
    enum.Enum: (__add_enum__, "string"),
    uuid.UUID: (__add_uuid__, "string"),
    type(None): (__add_none__, "string"),
}


__lxml_types_map__ = {k: v[0] for k, v in __lxml_mapping__.items()}
__lxml_hints_map__ = {k: v[1] for k, v in __lxml_mapping__.items()}
__lxml_hints_reverse_map__ = {v[1]: k for k, v in __lxml_mapping__.items() if k in [int, float, bool, str]}


# functions
def etree_as_string(element, pretty_print=True, xml_declaration=False, encoding="utf-8", as_bytes=False):
    """
    :type element: _Element
    :type pretty_print: bool
    :type xml_declaration: bool
    :type encoding: str
    :type as_bytes: bool
    :rtype: str|bytes
    """
    result = tostring(element, pretty_print=pretty_print, xml_declaration=xml_declaration, encoding=encoding)
    if not as_bytes:
        result = result.decode(encoding)
    return result


def detect_lxml_type_hint(value) -> Optional[str]:
    """Detects typehint for Element tree item
    :param value: Value that would be added to element
    :type value: object
    :return: Hinted data type
    :rtype: str|None
    """
    hinted_value = None
    for known_type, hint in __lxml_hints_map__.items():
        if isinstance(value, known_type):
            hinted_value = hint
            break
    return hinted_value


def etree_find_xml(element, path, namespaces=None, **kwargs):
    """
    :param element: Element object to extract value
    :type element: _Element
    :param path: Subtag name
    :type path: str
    :param namespaces: Namespaces for XML find mapping
    :type namespaces: dict
    :param kwargs: Other optional flags (default only support now)
    :type kwargs: dict
    :return: Extracted value
    :rtype: _Element
    """
    # check params
    if not isinstance(element, _Element):
        raise InvalidParamTypeError("Etree subtag query. Improperly configured element param data type: %s" % element)
    if not isinstance(path, str):
        raise InvalidParamTypeError("Etree subtag query. Improperly configured path param data type: %s" % path)

    try:
        # extract child and text
        child = element.find(path, namespaces=namespaces)
        if child is None:
            raise InvalidBodyStructureError("Etree subtag query. Could not locate child path with name = %s" % path)
        return child
    except Exception as e:
        if not isinstance(e, ApiError):
            logger.error("Value extraction unknown error: <%s> %s" % (e.__class__.__name__, e))
            e = ServerError("Etree subtag query. Could not locate extract value with some unhandled exception.")
        if "default" in kwargs.keys():
            return kwargs["default"]
        else:
            raise e


def etree_find(element, path, req_type=None, allow_none=False, namespaces=None, **kwargs):
    """
    :param element: Element object to extract value
    :type element: _Element
    :param path: Subtag name
    :type path: str
    :param req_type: Object type for additional validation
    :type req_type: type
    :param allow_none: Flag to raise exception in case of None value on tag
    :type allow_none: bool
    :param namespaces: Namespaces for XML find mapping
    :type namespaces: dict
    :param kwargs: Other optional flags (default only support now)
    :type kwargs: dict
    :return: Extracted value
    """
    if not isinstance(element, _Element):
        raise InvalidParamTypeError("Etree subtag query. Improperly configured element param data type: %s" % element)
    if not isinstance(path, str):
        raise InvalidParamTypeError("Etree subtag query. Improperly configured path param data type: %s" % path)

    try:
        # extract child and text
        child = element.find(path, namespaces=namespaces)
        if child is None:
            raise InvalidBodyStructureError("Etree subtag query. Could not locate child path with name = %s" % path)
        result = child.text

        if result is not None:
            if req_type is not None and not isinstance(result, req_type):
                # validate result type through required in param data type and converting to it
                try:
                    result = req_type(result)
                except (ValueError, TypeError):
                    raise InvalidParamTypeError("Invalid data type for params %s" % path)
            elif result is not None:
                # validate result type through typeHint detecting in path and converting to ot
                hinted_type = child.get("typeHint")
                if hinted_type is not None and hinted_type in __lxml_hints_reverse_map__.keys():
                    try:
                        result = __lxml_hints_reverse_map__[hinted_type](result)
                    except Exception:
                        pass
        elif not allow_none:
            raise InvalidParamTypeError("Etree subtag query. Child path value is empty for name = %s" % path)

        return result
    except Exception as e:
        if not isinstance(e, ApiError):
            logger.error("Value extraction unknown error: <%s> %s" % (e.__class__.__name__, e))
            e = ServerError("Etree subtag query. Could not locate extract value with some unhandled exception.")
        if "default" in kwargs.keys():
            return kwargs["default"]
        else:
            raise e
