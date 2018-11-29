# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging

from sqlalchemy import inspect
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.hybrid import hybrid_property


__all__ = [
    'ResponseEncodableMixin'
]

logger = logging.getLogger(__name__)

class ResponseEncodableMixin(object):

    def response_encode(self, request=None) -> dict:
        """ Mixin to mark object support JSON serialization with JsonEncoder class

        :type request: lamb.utils.LambRequest
        :return: Encoded represenation of object
        :rtype: dict
        """
        if isinstance(self.__class__, DeclarativeMeta):
            result = dict()
            # append plain columns
            ins = inspect(self)
            for column in ins.mapper.column_attrs.keys():
                result[column] = getattr(self, column)

            # append hybrid properties
            ins = inspect(self.__class__)
            for i in inspect(self.__class__).all_orm_descriptors:
                if type(i) == hybrid_property:
                    result[i.__name__] = getattr(self, i.__name__)
            return result
        else:
            raise NotImplementedError('ResponseEncodableMixin response_encode method on non DeclarativeMeta '
                                      'should be implemented in subclass')
