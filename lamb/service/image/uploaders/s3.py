# -*- coding: utf-8 -*-

import logging
import tempfile

from typing import Optional
from django.conf import settings
from boto3.session import Session as AWSSession

from lamb.utils import LambRequest
from lamb import exc
from .base import BaseUploader, PILImage

logger = logging.getLogger(__name__)

__all__ = ['ImageUploadServiceAmazonS3']


class ImageUploadServiceAmazonS3(BaseUploader):
    """
    Amazon S3 image uploader


    """
    aws_session: AWSSession

    def __init__(self, envelope_folder: Optional[str] = None):
        super().__init__(envelope_folder=envelope_folder)
        # constrict session
        self.aws_session = AWSSession(
            aws_access_key_id=settings.LAMB_AWS_ACCESS_KEY,
            aws_secret_access_key=settings.LAMB_AWS_SECRET_KEY
        )
        s3 = self.aws_session.resource('s3')

        # find bucket
        exist_buckets = [b.name for b in s3.buckets.all()]
        if settings.LAMB_AWS_BUCKET_NAME not in exist_buckets:
            logger.warning('Have not found S3 %s bucket' % settings.LAMB_AWS_BUCKET_NAME)
            raise exc.ServerError('AWS bucket for store image not exist')
        self.bucket = s3.Bucket(settings.LAMB_AWS_BUCKET_NAME)

    def store_image(self, image: PILImage.Image,
                    proposed_file_name: str,
                    request: LambRequest,
                    image_format: Optional[str] = None) -> str:
        """ Implements specific storage logic
        :return: URL of stored image
        """
        with tempfile.TemporaryFile() as tf:
            # store image in temp file
            relative_path = self.construct_relative_path(proposed_file_name)
            logger.debug('Processing image: <%s, %s>: %s to %s'
                         % (image.format, proposed_file_name, image, relative_path))
            image.save(
                tf,
                image_format or image.format,
                quality=settings.LAMB_IMAGE_UPLOAD_QUALITY
            )
            tf.seek(0)

            # construct mime/type
            image_mime_type = 'image/%s' % image.format.lower()

            # upload image
            try:
                _ = self.bucket.put_object(
                    ACL='public-read',
                    Body=tf,
                    Key=relative_path,
                    ContentType=image_mime_type
                )
                uploaded_url = 'https://{}.amazonaws.com/{}/{}'.format(
                    settings.LAMB_AWS_BUCKET_ZONE, self.bucket.name, relative_path)
                return uploaded_url
            except Exception as e:
                raise exc.ServerError('Failed to save image') from e
