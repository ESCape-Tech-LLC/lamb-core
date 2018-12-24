# -*- coding: utf-8 -*-

import json
import logging
import sqlalchemy as sa

from typing import List
from dataclasses import asdict
from sqlalchemy import types
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import VARCHAR, BIGINT, JSONB
from sqlalchemy.ext.declarative import AbstractConcreteBase

from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin
from lamb.json.encoder import JsonEncoder
from lamb import exc

from .uploaders.types import ImageUploadSlice, UploadedSlice

__all__ = ['AbstractImage', 'UploadedSlicesType']

logger = logging.getLogger(__name__)


class UploadedSlicesType(types.TypeDecorator):
    """ Storage for UploadedSlice items

    Use different ways to store internal data for different diaclets:
        - postgresql: will use JSONB field type as storage
        - else: will use VARCHAR field type as storage

    TODO: check with non PostgreSQL backend
    """
    impl = sa.VARCHAR
    python_type = list

    def __init__(self, *args, encoder_class=JsonEncoder, **kwargs):
        self._encoder_class = encoder_class
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        # check params
        if value is None:
            return value

        if not isinstance(value, list):
            logger.warning('Invalid data type to store as image slices: %s' % value)
            raise exc.ServerError('Invalid data type to store as image slices')
        if not all([isinstance(s, UploadedSlice) for s in value]):
            logger.warning('Invalid data type to store as image slices: %s' % value)
            raise exc.ServerError('Invalid data type to store as image slices')

        # store data
        if dialect.name == 'postgresql':
            value = [asdict(v) for v in value]
        else:
            value = json.dumps(value, cls=self._encoder_class)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if dialect.name != 'postgresql':
                value = json.loads(value)

            if not isinstance(value, list):
                logger.warning('Invalid data type to store as image slices: %s' % value)
                raise exc.ServerError('Invalid data type to store as image slices')
            try:
                value = [UploadedSlice(**v) for v in value]
            except Exception as e:
                raise

        return value


class AbstractImage(ResponseEncodableMixin, AbstractConcreteBase, DeclarativeBase):
    """
    Abstract class for Images storage.

    Stores information about image_id and several urls for different size of image.
    This mapping does not produce any tables in database, subclass to your own Image model to create storage.

    Note:
        When subclassing, you should provide:
         - `__polymorphic_identity__` value (define your own enum for valid values) on `__mapper_args__`,
         - `__table_name__`

    Uploaded slices info json is stored in `slices_info` by `uploaders.utlis.upload_image`.
    Polymorphic identity value is stored in `image_type`, do not set directly.
    """
    ABSTRACT_IMAGE_TYPE: str = 'ABSTRACT'

    # columns
    image_id = Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    # slices_info = Column(JSONB, nullable=False)
    slices_info = Column(UploadedSlicesType, nullable=False)
    image_type = Column(VARCHAR, nullable=False)

    # meta
    __slicing__: List[ImageUploadSlice]

    __abstract__ = True

    __mapper_args__ = {
        'polymorphic_on': image_type,
        'polymorphic_identity': ABSTRACT_IMAGE_TYPE
    }
