from __future__ import annotations

import os
from typing import BinaryIO, Optional, Union

import furl

from django.conf import settings

from lamb import exc
from lamb.utils import LambRequest

from .base import BaseUploader, PILImage

__all__ = ["ImageUploadServiceDisk"]


# TODO: add support for folder other then static
# TODO: LAMB_STATIC_URL is not defined at settings in general - add to settings and make agnostic


class ImageUploadServiceDisk(BaseUploader):
    """Local folder uploader"""

    def store_image(
        self,
        image: Union[PILImage.Image, BinaryIO],
        proposed_file_name: str,
        request: LambRequest,
        image_format: Optional[str] = None,
    ) -> str:
        """
        Implements specific storage logic

        :return: URL of stored image
        """
        try:
            # prepare file path and check envelope folder exist
            static_relative_path = self.construct_relative_path(proposed_file_name)
            output_file_path = os.path.join(settings.LAMB_STATIC_FOLDER, static_relative_path)
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

            # store file on disk
            if isinstance(image, PILImage.Image):
                image.save(output_file_path, image_format or image.format, quality=settings.LAMB_IMAGE_UPLOAD_QUALITY)
            else:
                image.seek(0)
                with open(output_file_path, "wb") as f:
                    f.write(image.read())

            # get result url
            _url = furl.furl(settings.LAMB_STATIC_URL)
            _url.path.add(static_relative_path)
            result = _url.url
            result = request.build_absolute_uri(result)
            return result
        except Exception as e:
            raise exc.ServerError("Failed to save image") from e
