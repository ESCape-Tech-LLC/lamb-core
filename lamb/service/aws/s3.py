from __future__ import annotations

import dataclasses
import logging
import re
import warnings
from typing import IO, Any, BinaryIO

import botocore.exceptions
from botocore.config import Config
from furl import furl

from lamb import exc
from lamb.lamb_settings import settings, settings_config
from lamb.json.mixins import ResponseEncodableMixin

from ...utils.core import compact
from .base import AWSBase

if settings_config == "django":
    from django.core.files.uploadedfile import InMemoryUploadedFile
else:
    from fastapi import UploadFile as InMemoryUploadedFile


logger = logging.getLogger(__name__)

__all__ = ["S3Uploader", "S3BucketConfig"]


@dataclasses.dataclass
class S3BucketConfig(ResponseEncodableMixin):
    bucket_name: str | None = None
    region_name: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    endpoint_url: str | None = None
    bucket_url: str | None = None
    check_buckets_list: bool = True
    connect_timeout: float | None = None
    read_timeout: float | None = None

    def response_encode(self, request=None) -> dict:
        return dataclasses.asdict(self)


class S3Uploader(AWSBase):
    _conn_cfg: S3BucketConfig

    def __init__(
        self,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        bucket_name: str | None = None,
        region_name: str | None = None,
        endpoint_url: str | None = None,
        bucket_url: str | None = None,
        conn_cfg: S3BucketConfig | None = None,
        *args,
        **kwargs,
    ):
        # inject defaults
        if conn_cfg is not None:
            self._conn_cfg = conn_cfg
        else:
            warnings.warn(
                "Use of deprecated S3Uploader args, use S3BucketConfig instead", DeprecationWarning, stacklevel=2
            )
            self._conn_cfg = S3BucketConfig(
                bucket_name=bucket_name or settings.LAMB_AWS_BUCKET_NAME,
                region_name=region_name or settings.LAMB_AWS_REGION_NAME,
                access_key=aws_access_key_id or settings.LAMB_AWS_ACCESS_KEY,
                secret_key=aws_secret_access_key or settings.LAMB_AWS_SECRET_KEY,
                endpoint_url=endpoint_url or settings.LAMB_AWS_ENDPOINT_URL,
                bucket_url=bucket_url or settings.LAMB_AWS_BUCKET_URL,
            )

        # process
        super().__init__(
            *args,
            aws_access_key_id=self._conn_cfg.access_key,
            aws_secret_access_key=self._conn_cfg.secret_key,
            **kwargs,
        )

        config_kw = compact(
            {
                "signature_version": "s3v4",
                "connect_timeout": self._conn_cfg.connect_timeout,
                "read_timeout": self._conn_cfg.read_timeout,
            }
        )
        logger.debug(f"boto3 core config would be used: {config_kw}")
        config = Config(**config_kw)
        self._client = self._aws_session.client(
            service_name="s3",
            region_name=self._conn_cfg.region_name,
            endpoint_url=self._conn_cfg.endpoint_url,
            config=config,
        )

        # Check if bucket exists
        if self._conn_cfg.check_buckets_list:
            exist_buckets = [bucket["Name"] for bucket in self._client.list_buckets()["Buckets"]]
            if self._conn_cfg.bucket_name not in exist_buckets:
                logger.warning(f"Have not found S3 {bucket_name} bucket")
                raise exc.ServerError("Requested S3 bucket not exist")

    # properties wrappers
    @property
    def bucket_name(self) -> str | None:
        return self._conn_cfg.bucket_name

    @property
    def bucket_url(self) -> str | None:
        if self._conn_cfg.bucket_url is None:
            if self._conn_cfg.region_name is not None:
                result = f"https://s3.{self._conn_cfg.region_name}.amazonaws.com/{self._conn_cfg.bucket_name}/"
            else:
                result = f"https://{self._conn_cfg.bucket_name}.s3.amazonaws.com/"
        else:
            result = self._conn_cfg.bucket_url
        return result

    @property
    def endpoint_url(self) -> str | None:
        return self._conn_cfg.endpoint_url

    @property
    def client(self) -> object:
        """
        Returns low-level S3 client for direct methods access ability
        """
        return self._client

    # methods
    def put_object(
        self,
        body: BinaryIO | InMemoryUploadedFile | IO,
        relative_path: str,
        file_type: str,
        private: bool | None = False,
    ) -> str:
        """
        Uploads file to S3

        :param body: binary object to upload
        :param relative_path: relative path to store in
        :param file_type: file content type
        :param private: defines if to store as private file
        :return: uploaded file url
        """
        try:
            self._client.put_object(
                Bucket=self.bucket_name,
                ACL="private" if private else "public-read",
                Body=body,
                Key=relative_path,
                ContentType=file_type,
            )
        except botocore.exceptions.ClientError as e:
            raise exc.ExternalServiceError from e
        uploaded_url = furl(self.bucket_url)
        uploaded_url.path.add(relative_path)
        uploaded_url = uploaded_url.url
        logger.debug(f"Uploaded S3 URL: {uploaded_url}")
        return uploaded_url

    def get_object(self, relative_path: str, **kwargs):
        """
        Request object from S3 under relative path

        :param relative_path: relative path to stored file
        :param kwargs: additional low level client kwargs
        :return: S3 GET dict (low-level response)
        """
        try:
            kwargs = compact(kwargs)
            logger.info(
                f"Requesting S3 get_object: bucket={self.bucket_name}, path={relative_path}",
                extra={"bucket": self.bucket_name, "path": relative_path, "kwargs": kwargs},
            )
            result = self._client.get_object(Bucket=self.bucket_name, Key=relative_path, **kwargs)
        except botocore.exceptions.ClientError as e:
            raise exc.ExternalServiceError from e
        return result

    def delete_object(self, relative_path: str, **kwargs):
        """
        Removes file from S3

        :param relative_path: relative path to stored file
        """
        try:
            kwargs = compact(kwargs)
            self._client.delete_object(Bucket=self.bucket_name, Key=relative_path, **kwargs)
        except botocore.exceptions.ClientError as e:
            raise exc.ExternalServiceError from e

    def head_object(self, relative_path: str, **kwargs) -> dict[str, Any]:
        """
        Request low-level HEAD info from S3 storage about object

        :param relative_path: relative path to stored file
        :param kwargs: additional low level client kwargs
        :return: S3 HEAD info dict
        """
        try:
            kwargs = compact(kwargs)
            result = self._client.head_object(Bucket=self.bucket_name, Key=relative_path, **kwargs)
        except botocore.exceptions.ClientError as e:
            raise exc.ExternalServiceError from e
        return result

    def generate_presigned_url(self, relative_path: str, expires_in: int | None = 3600) -> str:
        """
        Generates pre-signed url for a stored in S3 file

        :param relative_path: stored file relative path
        :param expires_in: interval of link expiry
        :return: pre-signed url
        """
        try:
            presigned_url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": relative_path},
                ExpiresIn=expires_in,
            )
        except botocore.exceptions.ClientError as e:
            raise exc.ExternalServiceError from e
        logger.debug(f"Generated S3 presigned URL: {presigned_url}")
        return presigned_url

    @staticmethod
    def s3_parse_url(url: str) -> tuple[str, str, str]:
        # TODO: adapt to non AWS s3 storages
        """
        :return: Tuple of aws region name, bucket name, and file path
        """
        patterns = [
            r"^https?://s3.(?P<region>[\w-]+).amazonaws.com/(?P<bucket>[_\.\w-]+)/(?P<path>[/_\.\w-]+)$",
            r"^https?://(?P<bucket>[_\.\w-]+).s3-(?P<region>[\w-]+).amazonaws.com/(?P<path>[/_\.\w-]+)$",
        ]
        bucket_url = getattr(settings, "LAMB_AWS_BUCKET_URL", None)
        if bucket_url:
            patterns.insert(0, rf"^{bucket_url}/(?P<path>[/_\.\w-]+)$")
        match = None

        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                break

        if match is None:
            raise ValueError("No S3 url match found")

        if bucket_url:
            try:
                region = match.group("region")
            except IndexError:
                region = None

            try:
                bucket = match.group("bucket")
            except IndexError:
                bucket = None
        else:
            region = match.group("region")
            bucket = match.group("bucket")

        return region, bucket, match.group("path")

    @classmethod
    def remove_by_url(cls, url):
        # TODO: adapt to non AWS s3 storages
        region, bucket, path = cls.s3_parse_url(url)
        s3_uploader = cls(region_name=region, bucket_name=bucket)
        s3_uploader.delete_object(path)
