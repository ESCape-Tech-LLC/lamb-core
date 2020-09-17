# -*- coding: utf-8 -*-

import logging
import re
from typing import Optional, BinaryIO, Union, Tuple
from typing.io import IO

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from furl import furl

from lamb import exc
from .base import AWSBase

logger = logging.getLogger(__name__)

__all__ = ['S3Uploader']


class S3Uploader(AWSBase):

    def __init__(self,
                 aws_access_key_id: Optional[str] = settings.LAMB_AWS_ACCESS_KEY,
                 aws_secret_access_key: Optional[str] = settings.LAMB_AWS_SECRET_KEY,
                 bucket_name: Optional[str] = settings.LAMB_AWS_BUCKET_NAME,
                 region_name: Optional[str] = settings.LAMB_AWS_REGION_NAME,
                 endpoint_url: Optional[str] = settings.LAMB_AWS_ENDPOINT_URL,
                 bucket_url: Optional[str] = settings.LAMB_AWS_BUCKET_URL,
                 *args,
                 **kwargs):

        super(S3Uploader, self).__init__(aws_access_key_id, aws_secret_access_key, *args, **kwargs)

        self._client = self._aws_session.client('s3', region_name=region_name, endpoint_url=endpoint_url)

        # Check if bucket exists
        exist_buckets = [bucket['Name'] for bucket in self._client.list_buckets()['Buckets']]
        if bucket_name not in exist_buckets:
            logger.warning('Have not found S3 %s bucket' % bucket_name)
            raise exc.ServerError('AWS bucket %s does not exist' % bucket_name)

        # Fill instance variables
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.bucket_url = bucket_url

    def put_object(self, body: Union[BinaryIO, InMemoryUploadedFile, IO], relative_path: str,
                   file_type: str, private: Optional[bool] = False) -> str:
        """
        Uploads file to S3

        :param body: binary object to upload
        :param relative_path: relative path to store in
        :param file_type: file content type
        :param private: defines if to store as private file
        :return: uploaded file url
        """
        self._client.put_object(
            Bucket=self.bucket_name,
            ACL='private' if private else 'public-read',
            Body=body,
            Key=relative_path,
            ContentType=file_type
        )
        if self.bucket_url is None:
            if self.region_name is not None:
                bucket_url = f'https://s3.{self.region_name}.amazonaws.com/{self.bucket_name}/'
            else:
                bucket_url = f'http://{self.bucket_name}.s3.amazonaws.com/'
        else:
            bucket_url = self.bucket_url
        uploaded_url = furl(bucket_url)
        uploaded_url.path.add(relative_path)
        uploaded_url = uploaded_url.url
        logger.debug(f'Uploaded S3 URL: {uploaded_url}')
        return uploaded_url

    def delete_object(self, relative_path: str):
        """
        Removes file from S3

        :param relative_path: relative path to stored file
        """
        self._client.delete_object(
            Bucket=self.bucket_name,
            Key=relative_path
        )

    def generate_presigned_url(self, relative_path: str, expires_in: Optional[int] = 3600) -> str:
        """
        Generates presigned url for a stored in S3 file

        :param relative_path: stored file relative path
        :param expires_in: interval of link expiry
        :return: presigned url
        """
        presigned_url = self._client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': self.bucket_name, 'Key': relative_path},
            ExpiresIn=expires_in
        )
        logger.debug(f'Generated S3 presigned URL: {presigned_url}')
        return presigned_url

    @staticmethod
    def s3_parse_url(url: str) -> Tuple[str, str, str]:
        """
        :return: Tuple of aws region name, bucket name, and file path
        """

        patterns = (
            r'^https?://s3.(?P<region>[\w-]+).amazonaws.com/(?P<bucket>[_\.\w-]+)/(?P<path>[/_\.\w-]+)$',
            r'^https?://(?P<bucket>[_\.\w-]+).s3-(?P<region>[\w-]+).amazonaws.com/(?P<path>[/_\.\w-]+)$',
        )
        match = None

        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                break

        if match is None:
            raise ValueError('No S3 url match found')

        return match.group('region'), match.group('bucket'), match.group('path')
