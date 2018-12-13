from typing import List

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import VARCHAR, BIGINT, JSONB
from sqlalchemy.ext.declarative import AbstractConcreteBase

from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin

from .uploaders.types import ImageUploadSlice

__all__ = ['AbstractImage']


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
    slices_info = Column(JSONB, nullable=False)
    image_type = Column(VARCHAR, nullable=False)

    # meta
    __slicing__: List[ImageUploadSlice]

    __abstract__ = True

    __mapper_args__ = {
        'polymorphic_on': image_type,
        'polymorphic_identity': ABSTRACT_IMAGE_TYPE
    }
