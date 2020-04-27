# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import abc
import json
import logging
import enum
from typing import Type

from django.core.cache import cache
from sqlalchemy import Column, VARCHAR, TEXT
from lamb import exc
from lamb.db.patterns import DbEnum
from lamb.db.context import lamb_db_context
from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin


__all__ = [
    'AbstractSettingsStorage', 'AbstractSettingsValue',
    'BaseConverter', 'SimpleTypeConverter', 'JsonConverter', 'IntBooleanConverter'

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


class AbstractSettingsValueCache:
    """Descriptor that cache `AbstractSettingsValue` values.
    """

    @staticmethod
    def key_func(settings_cls: Type['AbstractSettingsValue'], key: str):
        return f"{settings_cls.__cache_prefix__}_{key}"

    @classmethod
    def clear(cls, settings_cls: Type['AbstractSettingsValue']):
        """Delete values of all settings members from a cache."""
        cache.delete_many([cls.key_func(settings_cls, key) for key in settings_cls.__members__])

    def __get__(self, obj: 'AbstractSettingsValue', objtype: Type['AbstractSettingsValue']) -> 'AbstractSettingsStorage':
        value = None
        if obj._cached and obj.__cache_timeout__ != 0:
            value = cache.get(self.key_func(obj, obj.value))
        return value

    def __set__(self, obj: 'AbstractSettingsValue', value: 'AbstractSettingsStorage'):
        timeout = obj.__cache_timeout__
        values_dict = {k: getattr(value, k) for k in obj.__class__.__attrib_mapping__.values()}
        if obj._cached and timeout != 0:
            cache.set(
                key=self.key_func(obj, obj.value),
                value=value.__class__(**values_dict),
                timeout=timeout
            )

    def __delete__(self, obj: 'AbstractSettingsValue'):
        if obj._cached and obj.__cache_timeout__ != 0:
            cache.delete(self.key_func(obj, obj.value))


@enum.unique
class AbstractSettingsValue(DbEnum):
    """Settings storage processor.

       Example:

        from lamb.ext.settings import AbstractSettingsValue

        class TestCode(AbstractSettingsValue):
            __table_class__ = 'SettingsStorage'

            # Cache timeout, in seconds, to use for the cache. None - cache forever, 0 - do not use cache.
            __cache_timeout__ = 600

            # Prefix for settings keys in the cache
            __cache_prefix__ = 'lamb_settings'

            # Settings variable
            settings1 = ('settings1', 900, 'Description', int, None)

            # Variable with caching disabled
            settings2 = ('settings2', 900, 'Description', int, None, False)

    )
    """

    __table_class__ = None
    __attrib_mapping__ = {
        'val': 'value',
        'description': 'description',
        'disclaimer': 'disclaimer'
    }

    __cache_timeout__ = None
    __cache_prefix__ = 'lamb_settings'
    _cached_item = AbstractSettingsValueCache()


    def __new__(cls, code, default, default_description, converter, default_disclaimer, cached=True, *args, **kwargs):
        """
        :param code:
        :param default:
        :param default_description:
        :param converter:
        :param default_disclaimer:
        :param cached: cache variable values if True. Cache is enabled by default.
        """
        obj = object.__new__(cls)
        obj._value_ = code
        obj.default = default
        obj._default_description = default_description
        obj._default_disclaimer = default_disclaimer
        obj._converter = None  # type: BaseConverter
        obj._cached = cached

        if any(converter is simple_type for simple_type in (int, str, float)):
            obj._converter = SimpleTypeConverter(converter)
        elif any(converter is json_type for json_type in (dict, list)):
            obj._converter = JsonConverter()
        else:
            obj._converter = converter
        return obj

    @classmethod
    def cache_clear(cls):
        """Clear the cache of settings values."""
        AbstractSettingsValueCache.clear(cls)

    def __getattribute__(self, key):
        if key[:2] != '__':
            mapping = self.__class__.__attrib_mapping__
            if key in mapping:
                mapped_key = mapping[key]
                db_item = self._cached_item
                if db_item:
                    # use cached value
                    result = getattr(db_item, mapped_key)
                else:
                    with lamb_db_context() as session:
                        self._cached_item = db_item = self._db_item(session)
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
                    self._cached_item = db_item
        super().__setattr__(key, value)

    def _setup_db_item(self, item):
        item = super()._setup_db_item(item=item)
        item.value = self._converter.process_result_value(self.default)
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
