import logging
from typing import Callable, Optional, Union, List
from functools import singledispatch

from lxml.etree import _Element as EtreeElement, _ElementTree as Etree
import dpath
from lamb import exc

from .lxml_protocols import __lxml_hints_reverse_map__

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
    dpath_kwargs = dict()
    if 'default' in kwargs:
        dpath_kwargs['default'] = kwargs.pop('default', None)
    result = _dpath_value_inner(dict_object, key_path,
                                req_type, allow_none, **dpath_kwargs)
    if transform is not None:
        return transform(result, **kwargs)
    return result


@singledispatch
def _dpath_value_inner(dict_object: Optional[dict] = None,
                       path: Union[str, List[str]] = None,
                       req_type: Optional[Callable] = None,
                       allow_none: bool = False,
                       **kwargs):
    """
    Implementation for dict
    :param dict_object: Dict to find data
    :param path: Query string
    :param req_type: Type of argument that expected
    :param allow_none: Return None withour exception if leaf exist and equal to None
    :return:
    """
    def type_convert(req_type, value):
        if req_type is None:
            return value
        if isinstance(value, req_type):
            return value
        try:
            value = req_type(value)
            return value
        except (ValueError, TypeError) as e:
            raise exc.InvalidParamTypeError('Invalid data type for param %s' % path,
                                            error_details={'key_path': path}) from e
    try:
        items = dpath.util.values(dict_object, path)
        result = items[0]

        if req_type is None:
            return result

        if result is None:
            if allow_none:
                return None
            else:
                raise exc.InvalidParamTypeError('Invalid data type for param %s' % path,
                                                error_details={'key_path': path})

        result = type_convert(req_type, result)
        return result
    except IndexError as e:
        if 'default' in kwargs.keys():
            return kwargs['default']
        else:
            raise exc.InvalidBodyStructureError(
                'Could not extract param for key_path %s from provided dict data' % path,
                error_details={'key_path': path}) from e
    except AttributeError as e:
        raise exc.ServerError('Invalid key_path type for querying in dict',
                              error_details={'key_path': path}) from e


@_dpath_value_inner.register(EtreeElement)
@_dpath_value_inner.register(Etree)
def _etree_find(element: Union[EtreeElement, Etree],
                path: str,
                req_type: Optional[Callable] = None,
                allow_none: bool = False,
                namespaces: Optional[dict] = None,
                **kwargs):
    """
    :param element: Element object to extract value
    :param path: Subtag name
    :param req_type: Object type for additional validation
    :param allow_none: Flag to raise exception in case of None value on tag
    :param namespaces: Namespaces for XML find mapping
    :return: Extracted value
    """
    if not isinstance(element, (EtreeElement, Etree)):
        raise exc.InvalidParamTypeError('Etree subtag query. Improperly configured element param data type: %s' % element)
    if not isinstance(path, str):
        raise exc.InvalidParamTypeError('Etree subtag query. Improperly configured path param data type: %s' % path)

    try:
        # extract child and text
        child = element.find(path, namespaces=namespaces)
        if child is None:
            raise exc.InvalidBodyStructureError('Etree subtag query. Could not locate child path with name = %s' % path)
        result = child.text

        if result is not None:
            if req_type is not None and not isinstance(result, req_type):
                # validate result type through required in param data type and converting to it
                try:
                    result = req_type(result)
                except(ValueError, TypeError):
                    raise exc.InvalidParamTypeError('Invalid data type for params %s' % path)
            elif result is not None:
                # validate result type through typeHint detecting in path and converting to ot
                hinted_type = child.get('typeHint')
                if hinted_type is not None and hinted_type in __lxml_hints_reverse_map__.keys():
                    try:
                        result = __lxml_hints_reverse_map__[hinted_type](result)
                    except: pass
        elif not allow_none:
            raise exc.InvalidParamTypeError('Etree subtag query. Child path value is empty for name = %s' % path)

        return result
    except Exception as e:
        if not isinstance(e, exc.ApiError):
            logger.error('Value extraction unknown error: <%s> %s' % (e.__class__.__name__, e))
            e = exc.ServerError('Etree subtag query. Could not locate extract value with some unhandled exception.')
        if 'default' in kwargs.keys():
            return kwargs['default']
        else:
            raise e
