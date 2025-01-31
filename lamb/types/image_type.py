from __future__ import annotations

import contextlib
import enum
import json
import logging
from dataclasses import asdict, dataclass
from typing import TypeVar

import sqlalchemy as sa
from botocore.exceptions import BotoCoreError
from django.conf import settings
from sqlalchemy import types
from sqlalchemy.dialects.postgresql import JSONB

from lamb import exc
from lamb.json import JsonEncoder
from lamb.json.mixins import ResponseEncodableMixin
from lamb.service.aws.s3 import S3Uploader

__all__ = [
    "Mode",
    "SliceRule",
    "ImageSlice",
    "IT",
    "ImageSlicesType",
    "ImageListSlicesType",
]


logger = logging.getLogger(__name__)


# uploading image rules
@enum.unique
class Mode(str, enum.Enum):
    """Image cropping mode for upload"""

    Resize = "resize"
    Crop = "crop"
    NoAction = "no_action"


@dataclass(frozen=True)
class SliceRule:
    """Image slicing descriptor. Previously title ImageUploadSlice"""

    title: str
    side: int
    mode: Mode
    suffix: str

    def __post_init__(self) -> None:
        if not isinstance(self.title, str):
            logger.warning(f"Invalid SliceRule title data type = {self.title}")
            raise exc.ServerError("Improperly configured image uploader")

        if not isinstance(self.side, int):
            logger.warning(f"Invalid SliceRule rib data type = {self.side}")
            raise exc.ServerError("Improperly configured image uploader")

        if not isinstance(self.mode, Mode):
            logger.warning(f"Invalid SliceRule mode data type = {self.mode}")
            raise exc.ServerError("Improperly configured image uploader")

        if not isinstance(self.suffix, str):
            logger.warning(f"Invalid SliceRule suffix data type = {self.suffix}")
            raise exc.ServerError("Improperly configured image uploader")


# base storage bricks
@dataclass(frozen=False)
class ImageSlice(ResponseEncodableMixin):
    """Real stored image single slice"""

    title: str
    mode: Mode | None
    url: str
    width: int | None
    height: int | None

    def response_encode(self, request=None):
        if "ImageUploadServiceAmazonS3" in settings.LAMB_IMAGE_UPLOAD_ENGINE:
            bucket_url = getattr(settings, "LAMB_AWS_BUCKET_URL", None)
            if bucket_url:
                s3_uploader = S3Uploader()
                _, _, path = s3_uploader.s3_parse_url(self.url)
                with contextlib.suppress(BotoCoreError):
                    self.url = s3_uploader.generate_presigned_url(path, 300)
        return asdict(self)


# database storage support
# TODO: check with non PostgreSQL backend
IT = TypeVar("IT", bound=ImageSlice)


class ImageSlicesType(types.TypeDecorator):  # noqa
    """
    Column type for storing list of ImageSlice objects

    :arg encoder_class: can be used to customize json encoding on non PostgreSQL engines
    :arg slice_class: can be used to specify subclass of `ImageSlice` that would be stored in slices
    """

    impl = sa.VARCHAR
    python_type = list

    _encoder_class: type[JsonEncoder]
    _slice_class: type[IT]

    def __init__(
        self, *args, encoder_class: type[JsonEncoder] = JsonEncoder, slice_class: type[IT] = ImageSlice, **kwargs
    ):
        self._encoder_class = encoder_class
        self._slice_class = slice_class

        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        # early return
        if value is None:
            return None

        # check params
        if not isinstance(value, list):
            logger.warning(f"Invalid data type to store as image slices: {value}")
            raise exc.ServerError("Invalid data type to store as image slices")
        if not all([isinstance(s, self._slice_class) for s in value]):
            logger.warning(f"Invalid data type to store as image slices: {value}, required class = {self._slice_class}")
            raise exc.ServerError("Invalid data type to store as image slices")

        # store data
        if dialect.name == "postgresql":
            value = [asdict(v) for v in value]
        else:
            value = json.dumps(value, cls=self._encoder_class)

        return value

    def process_result_value(self, value, dialect):
        # early return
        if value is None:
            return None

        # load data
        if dialect.name != "postgresql":
            value = json.loads(value)

        # check and convert
        if not isinstance(value, list):
            logger.warning(f"Invalid data type stored in database to interpret as ImagesSlices: {value}")
            raise exc.ServerError("Invalid data type to retrieve as image slices")

        try:
            value = [self._slice_class(**v) for v in value]
        except Exception as e:
            raise exc.ServerError("Could not convert database item to image slice") from e

        return value


class ImageListSlicesType(types.TypeDecorator):  # noqa
    """Column type that acts like List[ImageSlicesType] to store info about many images in one field
    :arg encoder_class: can be used to customize json encoding on non PostgreSQL engines
    :arg slice_class: can be used to specify subclass of `ImageSlice` that would be stored in slices
    """

    impl = sa.VARCHAR
    python_type = list

    _encoder_class: type[JsonEncoder]
    _slice_class: type[IT]

    def __init__(
        self, *args, encoder_class: type[JsonEncoder] = JsonEncoder, slice_class: type[IT] = ImageSlice, **kwargs
    ):
        self._encoder_class = encoder_class
        self._slice_class = slice_class

        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        # early return
        if value is None:
            return None

        # check params
        if not isinstance(value, list):
            logger.warning(f"Invalid data type to store as image slices: {value}")
            raise exc.ServerError("Invalid data type to store as image slices")
        if any([not isinstance(v, list) for v in value]):
            logger.warning(f"Invalid data type to store as image slices: {value}")
            raise exc.ServerError("Invalid data type to store as image slices")
        if any([not isinstance(item, self._slice_class) for v in value for item in v]):
            logger.warning(f"Invalid data type to store as image slices: {value}")
            raise exc.ServerError("Invalid data type to store as image slices")

        # store data
        if dialect.name == "postgresql":
            value = [[asdict(item) for item in v] for v in value]
        else:
            value = json.dumps(value, cls=self._encoder_class)

        return value

    def process_result_value(self, value, dialect):
        # early return
        if value is None:
            return None

        # load data
        if dialect.name != "postgresql":
            value = json.loads(value)

        # check and convert
        if not isinstance(value, list):
            logger.warning(f"Invalid data type stored in database to interpret as List of ImagesSlices: {value}")
            raise exc.ServerError("Invalid data type to retrieve as image slices")
        if any([not isinstance(v, list) for v in value]):
            logger.warning(f"Invalid data type stored in database to interpret as List of ImagesSlices: {value}")
            raise exc.ServerError("Invalid data type to retrieve as image slices")

        try:
            value = [[self._slice_class(**item) for item in v] for v in value]
        except Exception as e:
            raise exc.ServerError("Could not convert database item to image slice") from e

        return value
