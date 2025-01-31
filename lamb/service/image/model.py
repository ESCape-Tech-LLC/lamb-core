from __future__ import annotations

import logging
from typing import List

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import BIGINT, VARCHAR
from sqlalchemy.ext.declarative import AbstractConcreteBase

from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin
from lamb.types.image_type import ImageSlicesType, Mode, SliceRule

__all__ = ["AbstractImage", "ImageMixin"]


logger = logging.getLogger(__name__)


# declarative base and mixins
class ImageMixin(object):
    """Abstract mixin for image subclasses."""

    __slicing__: List[SliceRule] = [SliceRule("origin", -1, Mode.NoAction, "")]
    slices_info = Column(ImageSlicesType, nullable=False)


class AbstractImage(ImageMixin, ResponseEncodableMixin, AbstractConcreteBase, DeclarativeBase):
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

    ABSTRACT_IMAGE_TYPE: str = "ABSTRACT"

    # columns
    image_id = Column(BIGINT, nullable=False, primary_key=True, autoincrement=True)
    image_type = Column(VARCHAR, nullable=False)

    # meta
    __abstract__ = True

    __mapper_args__ = {"polymorphic_on": image_type, "polymorphic_identity": ABSTRACT_IMAGE_TYPE}
