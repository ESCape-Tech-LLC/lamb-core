import enum

from sqlalchemy import Column, BIGINT, ForeignKey

from lamb.service.image.model import AbstractImage
from lamb.service.image.uploaders import ImageUploadSlice, ImageUploadMode


@enum.unique
class ImageType(str, enum.Enum):
    ABSTRACT = AbstractImage.ABSTRACT_IMAGE_TYPE
    SIMPLE = 'simple'


class Image(AbstractImage):
    # meta
    __tablename__ = 'tests_image'


class SimpleImage(Image):
    # columns
    image_id = Column(
        BIGINT,
        ForeignKey(Image.image_id, onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        primary_key=True
    )

    __slicing__ = [
        ImageUploadSlice('origin', -1, ImageUploadMode.NoAction, ''),
        ImageUploadSlice('small', 100, ImageUploadMode.Resize, 'small'),
        ImageUploadSlice('thumb', 50, ImageUploadMode.Crop, 'thumb')
    ]

    # meta
    __tablename__ = 'tests_simple_image'

    __mapper_args__ = {
        'polymorphic_identity': ImageType.SIMPLE.value,
        'polymorphic_on': 'image_type',
    }

    __table_args__ = {
        'comment': 'Simple images storage table'
    }
