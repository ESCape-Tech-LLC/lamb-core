from __future__ import annotations

import logging
from typing import List

from sqlalchemy import Column, inspect
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import ColumnProperty, RelationshipProperty, SynonymProperty
from sqlalchemy.orm.attributes import QueryableAttribute

from lamb import exc

try:
    import cassandra
    from cassandra.cqlengine.models import Model as CassandraModel
except ImportError:
    cassandra = None
    CassandraModel = object()


__all__ = ["ResponseEncodableMixin"]

logger = logging.getLogger(__name__)


_DEFAULT_ATTRIBUTE_NAMES_REGISTRY = {}


class ResponseEncodableMixin(object):
    @classmethod
    def response_attributes(cls) -> List:
        return None

    def response_encode(self, request=None) -> dict:
        """Mixin to mark object support JSON serialization with JsonEncoder class

        :type request: lamb.utils.LambRequest
        :return: Encoded representation of object
        :rtype: dict
        """

        # Cassandra model is dict compatible,
        # return it as dict
        if cassandra and isinstance(self, CassandraModel):
            return dict(self)

        # cache
        if self.__class__ not in _DEFAULT_ATTRIBUTE_NAMES_REGISTRY:
            # check possibility to process
            _declarative = isinstance(self.__class__, DeclarativeMeta)
            _attributes_provided = self.response_attributes() is not None
            if not _declarative and not _attributes_provided:
                raise NotImplementedError(
                    "ResponseEncodableMixin subclass should implement non empty: "
                    "classmethod:response_attributes() or to be subclass of DeclarativeMeta to "
                    "use default encoder. In other case implement custom method "
                    "response_encode()"
                )

            # extract attribute names
            response_attributes = self.response_attributes()
            if response_attributes is None:
                # for DeclarativeMeta support auto descriptors discovery
                response_attributes = []
                ins = inspect(self.__class__)

                # append plain columns
                response_attributes.extend(ins.mapper.column_attrs.values())

                # append synonyms
                response_attributes.extend(ins.mapper.synonyms.values())

                # append hybrid properties
                response_attributes.extend(
                    # [ormd for ormd in ins.all_orm_descriptors if type(ormd) == hybrid_property]  # noqa: E721
                    [ormd for ormd in ins.all_orm_descriptors if isinstance(ormd, hybrid_property)]
                )

            # parse names
            response_attribute_names = []
            for orm_descriptor in response_attributes:
                if isinstance(orm_descriptor, str):
                    orm_attr_name = orm_descriptor
                elif isinstance(orm_descriptor, Column):
                    orm_attr_name = orm_descriptor.name
                elif isinstance(
                    orm_descriptor, (ColumnProperty, RelationshipProperty, QueryableAttribute, SynonymProperty)
                ):
                    orm_attr_name = orm_descriptor.key
                elif isinstance(orm_descriptor, hybrid_property):
                    orm_attr_name = orm_descriptor.__name__
                elif isinstance(orm_descriptor, property):
                    orm_attr_name = orm_descriptor.fget.__name__
                else:
                    logger.warning(f"Unsupported orm_descriptor type: {orm_descriptor, orm_descriptor.__class__}")
                    raise exc.ServerError("Could not serialize data")
                response_attribute_names.append(orm_attr_name)
            logger.debug(f"caching response attribute keys: {self.__class__.__name__} -> {response_attribute_names}")
            _DEFAULT_ATTRIBUTE_NAMES_REGISTRY[self.__class__] = response_attribute_names

        # encode data
        response_attribute_names = _DEFAULT_ATTRIBUTE_NAMES_REGISTRY[self.__class__]
        result = {orm_attr: getattr(self, orm_attr) for orm_attr in response_attribute_names}
        return result
