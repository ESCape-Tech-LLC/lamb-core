# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging

from typing import Optional, List
from sqlalchemy import inspect, Column
from sqlalchemy.orm import ColumnProperty, RelationshipProperty
from sqlalchemy.orm.attributes import QueryableAttribute, InstrumentedAttribute
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.hybrid import hybrid_property
from lamb import exc
from lazy import lazy


__all__ = [
    'ResponseEncodableMixin'
]

logger = logging.getLogger(__name__)


_DEFAULT_ATTRIBUTE_NAMES_REGISTRY = {}


class ResponseEncodableMixin(object):

    @classmethod
    def response_attributes(cls) -> List:
        return None

    def response_encode(self, request=None) -> dict:
        """ Mixin to mark object support JSON serialization with JsonEncoder class

        :type request: lamb.utils.LambRequest
        :return: Encoded represenation of object
        :rtype: dict
        """
        if isinstance(self.__class__, DeclarativeMeta):
            # cache
            if self.__class__ not in _DEFAULT_ATTRIBUTE_NAMES_REGISTRY:
                # extract attribute names
                response_attributes = self.response_attributes()
                if response_attributes is None:
                    response_attributes = []
                    ins = inspect(self.__class__)

                    # append plain columns
                    response_attributes.extend(ins.mapper.column_attrs.values())

                    # append hybrid properties
                    response_attributes.extend([
                        ormd for ormd in ins.all_orm_descriptors if type(ormd) == hybrid_property
                    ])
                    # logger.debug(f'ResponseEncodableMixin attributes default used: {self.__class__.__name__} -> {response_attributes}')
                else:
                    # logger.debug(f'ResponseEncodableMixin attributes NON-default used: {self.__class__.__name__} -> {response_attributes}')
                    pass

                # parse names
                response_attribute_names = []
                for orm_descriptor in response_attributes:
                    # if isinstance(orm_descriptor, InstrumentedAttribute):
                    #     orm_descriptor = orm_descriptor.key
                    # if isinstance(orm_descriptor, QueryableAttribute):
                    #     orm_descriptor = orm_descriptor.property

                    if isinstance(orm_descriptor, str):
                        orm_attr_name = orm_descriptor
                    elif isinstance(orm_descriptor, Column):
                        orm_attr_name = orm_descriptor.name
                    elif isinstance(orm_descriptor, (ColumnProperty, RelationshipProperty, QueryableAttribute)):
                        orm_attr_name = orm_descriptor.key
                    elif isinstance(orm_descriptor, hybrid_property):
                        orm_attr_name = orm_descriptor.__name__
                    else:
                        logger.warning(f'Unsupported orm_descriptor type: {orm_descriptor, orm_descriptor.__class__}')
                        raise exc.ServerError('Could not serialize data')
                    response_attribute_names.append(orm_attr_name)
                logger.info(f'caching response attribute keys: {self.__class__.__name__} -> {response_attribute_names}')
                _DEFAULT_ATTRIBUTE_NAMES_REGISTRY[self.__class__] = response_attribute_names

            response_attribute_names = _DEFAULT_ATTRIBUTE_NAMES_REGISTRY[self.__class__]
            result = {orm_attr: getattr(self, orm_attr) for orm_attr in response_attribute_names}
            return result
        else:
            raise NotImplementedError('ResponseEncodableMixin response_encode method on non DeclarativeMeta '
                                      'should be implemented in subclass')
