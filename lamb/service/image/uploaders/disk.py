# -*- coding: utf-8 -*-

import os

from typing import Optional, Union, BinaryIO
from urllib.parse import urljoin
from django.conf import settings

from lamb.utils import LambRequest
from lamb import exc

from .base import BaseUploader, PILImage

__all__ = ['ImageUploadServiceDisk']


class ImageUploadServiceDisk(BaseUploader):
    """ Local folder uploader """

    def store_image(self, image: Union[PILImage.Image, BinaryIO],
                    proposed_file_name: str,
                    request: LambRequest,
                    image_format: Optional[str] = None) -> str:
        """
        Implements specific storage logic

        :return: URL of stored image
        """
        try:
            # prepare file path and check envelope folder exist
            static_relative_path = self.construct_relative_path(proposed_file_name)
            output_file_path = os.path.join(
                settings.LAMB_STATIC_FOLDER,
                static_relative_path
            )
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

            # store file on disk
            if isinstance(image, PILImage.Image):
                image.save(
                    output_file_path,
                    image_format or image.format,
                    quality=settings.LAMB_IMAGE_UPLOAD_QUALITY
                )
            else:
                image.seek(0)
                with open(output_file_path, 'wb') as f:
                    f.write(image.read())

            # get result url
            result = urljoin(settings.LAMB_STATIC_URL, static_relative_path)
            result = request.build_absolute_uri(result)
            return result
        except Exception as e:
            raise exc.ServerError('Failed to save image') from e
