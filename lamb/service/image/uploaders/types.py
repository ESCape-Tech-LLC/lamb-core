import enum
import logging
# noinspection PyCompatibility
from dataclasses import dataclass

from lamb import exc

__all__ = ['ImageUploadMode', 'ImageUploadSlice', 'UploadedSlice']

logger = logging.getLogger(__name__)


@enum.unique
class ImageUploadMode(str, enum.Enum):
    Resize = 'resize'
    Crop = 'crop'
    NoAction = 'no_action'


@dataclass(frozen=True)
class ImageUploadSlice:
    title: str
    side: int
    mode: ImageUploadMode
    suffix: str

    def __post_init__(self) -> None:
        if not isinstance(self.title, str):
            logger.warning('Invalid ImageUploadSlice title data type = %s' % self.title)
            raise exc.ServerError('Improperly configured image uploader')

        if not isinstance(self.side, int):
            logger.warning('Invalid ImageUploadSlice rib data type = %s' % self.side)
            raise exc.ServerError('Improperly configured image uploader')

        if not isinstance(self.mode, ImageUploadMode):
            logger.warning('Invalid ImageUploadSlice mode data type = %s' % self.mode)
            raise exc.ServerError('Improperly configured image uploader')

        if not isinstance(self.suffix, str):
            logger.warning('Invalid ImageUploadSlice suffix data type = %s' % self.suffix)
            raise exc.ServerError('Improperly configured image uploader')


@dataclass(frozen=True)
class UploadedSlice:
    title: str
    mode: ImageUploadMode
    url: str
    width: int
    height: int
