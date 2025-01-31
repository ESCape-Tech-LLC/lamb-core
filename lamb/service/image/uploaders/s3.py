from __future__ import annotations

import logging
import tempfile
from typing import BinaryIO, Optional, Union

from boto3.session import Session as AWSSession

from django.conf import settings

from lamb import exc
from lamb.service.aws.s3 import S3BucketConfig, S3Uploader
from lamb.utils import LambRequest

from .base import BaseUploader, PILImage

logger = logging.getLogger(__name__)

__all__ = ["ImageUploadServiceAmazonS3"]


class ImageUploadServiceAmazonS3(BaseUploader):
    """Amazon S3 image uploader"""

    aws_session: AWSSession

    def __init__(self, envelope_folder: Optional[str] = None, conn_cfg: Optional[S3BucketConfig] = None):
        super().__init__(envelope_folder=envelope_folder)

        if conn_cfg is None:
            logger.warning("s3_config not provided -> try auto discover from settings.LAMB_AWS_CONFIG['default']")
            conn_cfg = settings.LAMB_AWS_CONFIG["default"]

        self._s3_uploader = S3Uploader(conn_cfg=conn_cfg)

    def store_image(
        self,
        image: Union[PILImage.Image, BinaryIO],
        proposed_file_name: str,
        request: LambRequest,
        image_format: Optional[str] = None,
        private: Optional[bool] = False,
    ) -> str:
        """
        Implements specific storage logic

        :return: URL of stored image
        """
        with tempfile.TemporaryFile() as tf:
            # store image in temp file
            relative_path = self.construct_relative_path(proposed_file_name)
            logger.debug(f"Processing image: <{image_format}, {proposed_file_name}>: {image} to {relative_path}")

            if isinstance(image, PILImage.Image):
                image_format = image_format or image.format
                image.save(tf, image_format, quality=settings.LAMB_IMAGE_UPLOAD_QUALITY)
            else:
                image.seek(0)
                tf.write(image.read())
            tf.seek(0)

            # construct mime/type
            image_mime_type = f"image/{image_format.lower()}"

            # upload image
            try:
                uploaded_url = self._s3_uploader.put_object(
                    body=tf, relative_path=relative_path, file_type=image_mime_type, private=private
                )
                return uploaded_url
            except Exception as e:
                raise exc.ServerError("Failed to save image") from e

    def get_presigned_url(self, filename: str, expires_in: Optional[int] = 3600):
        relative_path = self.construct_relative_path(filename)
        presigned_url = self._s3_uploader.generate_presigned_url(relative_path, expires_in)
        logger.debug(f"Received S3 presigned URL: {presigned_url}")
        return presigned_url
