# -*- coding: utf-8 -*-

import logging
# import dpath.util
import dpath

from typing import Callable, Optional, Union, List, Any
from functools import singledispatch
from lxml.etree import _Element as EtreeElement, _ElementTree as Etree
from django.conf import Settings

from lamb import exc

from lamb.ext.lxml import __lxml_hints_reverse_map__

logger = logging.getLogger(__name__)

__all__ = ['dpath_value']


def dpath_value(dict_object: Union[Optional[dict], EtreeElement, Etree] = None,
                key_path: Union[str, List[str]] = None,
                req_type: Optional[Callable] = None,
                allow_none: bool = False,
                transform: Optional[Callable] = None,
                **kwargs):
    """ Search for object in Dict or XML document

        :param dict_object: Document (Dict or _ElementTree or _Element) to find data
        :param key_path: Query string
        :param req_type: Type of argument that expected
        :param allow_none: Return None withour exception if leaf exist and equal to None
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
        if isinstance(_result, req_type):
            return _result
        try:
            _result = req_type(_result)
            return _result
        except (ValueError, TypeError) as _e:
            raise exc.InvalidParamTypeError('Invalid data type for param %s' % key_path,
                                            error_details={'key_path': key_path}) from _e

    # query
    try:
        # get internal result
        logger.debug(f'start extract')
        result = _dpath_find_impl(dict_object, key_path=key_path, **kwargs)

        # check for none
        if result is None:
            if allow_none:
                return None
            else:
                raise exc.InvalidParamTypeError('Invalid data type for param %s' % key_path,
                                                error_details={'key_path': key_path})

        # apply type convert
        result = _type_convert(result)

        # apply transform
        if transform is not None:
            return transform(result)

        return result
    except Exception as e:
        logger.exception(f'extraction failed: {e}')
        if 'default' in kwargs.keys():
            return kwargs['default']
        elif isinstance(e, exc.ApiError):
            raise
        else:
            raise exc.ServerError('Failed to parse params due unknown error') from e


@singledispatch
def _dpath_find_impl(dict_object: Optional[dict] = None,
                     key_path: Union[str, List[str]] = None,
                     **_) -> Any:
    """
    Implementation for dict
    :param dict_object: Dict to find data
    :param key_path: Query string
    :return: Extracted value
    """

    try:
        items = dpath.util.values(dict_object, key_path)  # type: List[Any]
        result = items[0]
        return result
    except IndexError as e:
        raise exc.InvalidBodyStructureError(
            'Could not locate field for key_path %s from provided dict data' % key_path,
            error_details={'key_path': key_path}) from e
    except AttributeError as e:
        raise exc.ServerError('Invalid key_path type for querying in dict',
                              error_details={'key_path': key_path}) from e


@_dpath_find_impl.register(EtreeElement)
@_dpath_find_impl.register(Etree)
def _etree_find_impl(element: Union[EtreeElement, Etree],
                     key_path: str,
                     namespaces: Optional[dict] = None,
                     **_) -> Any:
    """
    :param element: Element object to extract value
    :param key_path: Subtag name
    :param namespaces: Namespaces for XML find mapping
    :return: Extracted value
    """
    if not isinstance(element, (EtreeElement, Etree)):
        logger.warning('Improperly configured element param data type: %s' % element)
        raise exc.InvalidParamTypeError('ArgParsing. Improperly configured param source')
    if not isinstance(key_path, str):
        logger.warning('Improperly configured key_path param data type: %s' % key_path)
        raise exc.InvalidParamTypeError('ArgParsing. Improperly configured param search key_path')

    try:
        # extract child and text
        child = element.find(key_path, namespaces=namespaces)
        if child is None:
            raise exc.InvalidBodyStructureError(
                'Could not extract param for key_path %s from provided XML data' % key_path,
                error_details={'key_path': key_path})
        result = child.text

        # try auto-discover data type
        if result is not None:
            # validate result type through typeHint detecting in key_path and converting to ot
            hinted_type = child.get('typeHint')
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
            'Could not extract param for key_path %s from provided XML data' % key_path,
            error_details={'key_path': key_path}) from e
    except Exception as e:
        raise exc.ServerError(
            'Etree subtag query. Could not locate extract value with some unhandled exception.') from e


@_dpath_find_impl.register(Settings)
def _django_conf_impl(settings: Settings, key_path: str) -> Any:
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
        raise exc.InvalidBodyStructureError(f'Could not locate field for key_path = {key_path} from settings object',
                                            error_details={'key_path': key_path}) from e
