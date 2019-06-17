# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import abc
import json
import logging
import enum

from sqlalchemy import Column, VARCHAR, TEXT
from lamb import exc
from lamb.db.patterns import DbEnum
from lamb.db.context import lamb_db_context
from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin


__all__ = [
    'AbstractSettingsStorage', 'AbstractSettingsValue'
]


logger = logging.getLogger(__name__)


# system configs
class BaseConverter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def process_bind_param(self, value):
        logger.warning(f'Call to abstract method process_bind_param'
                       f' on class = {self.__class__.__name__} with value = {value}')
        raise exc.ServerError('Invalid server configs')

    @abc.abstractmethod
    def process_result_value(self, value):
        logger.warning(f'Call to abstract method process_result_value'
                       f' on class = {self.__class__.__name__} with value = {value}')


class SimpleTypeConverter(BaseConverter):
    def __init__(self, req_type):
        super().__init__()
        self.req_type = req_type

    def process_bind_param(self, value):
        if value is not None:
            return self.req_type(value)
        return None

    def process_result_value(self, value):
        if value is not None:
            return str(value)
        return None


class JsonConverter(BaseConverter):
    def process_bind_param(self, value):
        if value is not None:
            return json.loads(value)
        return None

    def process_result_value(self, value):
        if value is not None:
            return json.dumps(value)
        return None


class IntBooleanConverter(BaseConverter):
    def process_bind_param(self, value):
        if value is None:
            return None
        try:
            value = int(value)
            return value > 0
        except:
            return None

    def process_result_value(self, value):
        if value is None:
            return None
        if not isinstance(value, bool):
            raise exc.ServerError('Invalid data type for IntBooleanConverter flush to db process: %s' % value)
        if value:
            return '1'
        else:
            return '0'


@enum.unique
class AbstractSettingsValue(DbEnum):

    __table_class__ = None
    __attrib_mapping__ = {
        'val': 'value',
        'description': 'description',
        'disclaimer': 'disclaimer'
    }

    def __new__(cls, code, default, default_description, converter, default_disclaimer, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.default = default
        obj._default_description = default_description
        obj._default_disclaimer = default_disclaimer
        obj._converter = None  # type: BaseConverter

        if any(converter is simple_type for simple_type in (int, str, float)):
            obj._converter = SimpleTypeConverter(converter)
        elif any(converter is json_type for json_type in (dict, list)):
            obj._converter = JsonConverter()
        else:
            obj._converter = converter
        return obj

    def __getattribute__(self, key):
        if key[:2] != '__':
            mapping = self.__class__.__attrib_mapping__
            if key in mapping:
                mapped_key = mapping[key]
                with lamb_db_context() as session:
                    db_item = self._db_item(session)
                    result = getattr(db_item, mapped_key)
                    try:
                        if result is not None and key=='val':
                            result = self._converter.process_bind_param(result)
                    except Exception as e:
                        logger.error('Settings convert failed: %s' % e)
                        raise exc.ServerError('Improperly configured settings values') from e
                    return result
        return super().__getattribute__(key)

    def __setattr__(self, key, value):
        if key[:2] != '__':
            mapping = self.__class__.__attrib_mapping__
            if key in mapping:
                mapped_key = mapping[key]
                with lamb_db_context() as session:
                    db_item = self._db_item(session)
                    try:
                        if value is not None and key=='val':
                            value = self._converter.process_result_value(value)
                        db_item.__setattr__(mapped_key, value)
                    except Exception as e:
                        logger.error('Settings convert failed: %s' % e)
                        raise exc.ServerError('Improperly configured settings values') from e
                    session.commit()
        super().__setattr__(key, value)

    def _setup_db_item(self, item):
        item = super()._setup_db_item(item=item)
        item.value = self._converter.process_result_value(self.default)
        # item.value = self.default
        item.description = self._default_description
        item.disclaimer = self._default_disclaimer
        return item


class AbstractSettingsStorage(ResponseEncodableMixin, DeclarativeBase):
    __abstract__ = True
    # columns
    variable_name = Column(VARCHAR(40), nullable=False, primary_key=True)
    description = Column(TEXT, nullable=False)
    value = Column(TEXT, nullable=False)
    disclaimer = Column(TEXT, nullable=True)
