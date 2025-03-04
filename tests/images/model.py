import enum

# SQLAlchemy
from sqlalchemy import BIGINT, Column, ForeignKey

# Lamb Framework
from lamb.service.image.model import AbstractImage
from lamb.types.image_type import Mode, SliceRule


@enum.unique
class ImageType(str, enum.Enum):
    ABSTRACT = AbstractImage.ABSTRACT_IMAGE_TYPE
    SIMPLE = "simple"


class Image(AbstractImage):
    # meta
    __tablename__ = "tests_image"


class SimpleImage(Image):
    # columns
    image_id = Column(
        BIGINT, ForeignKey(Image.image_id, onupdate="CASCADE", ondelete="CASCADE"), nullable=False, primary_key=True
    )

    __slicing__ = [
        SliceRule(title="origin", side=-1, mode=Mode.NoAction, suffix=""),
        SliceRule(title="small", side=100, mode=Mode.Resize, suffix="small"),
        SliceRule(title="thumb", side=50, mode=Mode.Crop, suffix="thumb"),
    ]

    # meta
    __tablename__ = "tests_simple_image"

    __mapper_args__ = {
        "polymorphic_identity": ImageType.SIMPLE.value,
        "polymorphic_on": "image_type",
    }

    __table_args__ = {"comment": "Simple images storage table"}
