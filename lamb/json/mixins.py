# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

from sqlalchemy import inspect
from sqlalchemy.ext.declarative import DeclarativeMeta


__all__ = [
    'ResponseEncodableMixin'
]


class ResponseEncodableMixin(object):

    def response_encode(self, request=None):
        """ Mixin to mark object support JSON serialization with JsonEncoder class

        :type request: lamb.utils.LambRequest
        :return: Encoded represenation of object
        :rtype: dict
        """
        if isinstance(self.__class__, DeclarativeMeta):
            result = dict()
            ins = inspect(self)
            for column in ins.mapper.column_attrs.keys():
                result[column] = getattr(self, column)
            return result
        else:
            raise NotImplementedError('ResponseEncodableMixin response_encode method on non DeclarativeMeta '
                                      'should be implemented in subclass')
