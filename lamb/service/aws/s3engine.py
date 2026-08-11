from __future__ import annotations

import logging
import re
from typing import IO, Any, BinaryIO, Self

import boto3
import furl
from botocore.awsrequest import AWSRequest
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile, UploadedFile

from lamb import exc
from lamb.service.aws.config import S3BucketConfig
from lamb.utils.core import compact, lazy_ro

try:
    from types_boto3_s3.s3 import S3Client
except ImportError:
    from botocore.client import BaseClient as S3Client

try:
    import aioboto3
    import aiofiles
    from aiobotocore.config import AioConfig
    from aiobotocore.session import ClientCreatorContext
except ImportError:
    aioboto3 = None
    aiofiles = None
    AioConfig = None
    ClientCreatorContext = None

try:
    from types_aiobotocore_s3 import AsyncS3Client
except ImportError:
    AsyncS3Client = None

if AsyncS3Client is None:
    try:
        from aiobotocore.client import AioBaseClient as AsyncS3Client
    except ImportError:
        AsyncS3Client = None

logger = logging.getLogger(__name__)

__all__ = ["AsyncS3Engine", "S3Engine"]


class S3EngineBase:
    _config: S3BucketConfig

    def __init__(self, config: S3BucketConfig):
        self._config = config

    @classmethod
    def construct_sync_client(cls, conn_cfg: S3BucketConfig) -> S3Client:
        # Configure the S3 client with signature version s3v4 and specified region
        result = boto3.client(
            "s3",
            region_name=conn_cfg.region_name,
            config=Config(
                signature_version="s3v4",
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
            aws_access_key_id=conn_cfg.access_key,
            aws_secret_access_key=conn_cfg.secret_key,
            endpoint_url=conn_cfg.endpoint_url,
        )

        def _patch_signature_host(*, request: AWSRequest, **_):
            old_url = request.url
            _url = furl.furl(request.url)
            _url.netloc = conn_cfg.signature_host
            request.url = _url.url
            logger.debug(
                f"{cls.__name__}. generate_presigned_url: "
                f"signature host replaced with origin={old_url} -> target={request.url}"
            )

        if conn_cfg.signature_host:
            logger.warning(
                f"{cls.__name__}. generate_presigned_url: "
                f"register to meta events with signature_host={conn_cfg.signature_host}"
            )
            result.meta.events.register("before-sign.s3.GetObject", _patch_signature_host)

        return result

    @staticmethod
    def aws_s3_parse_url(url: str) -> tuple[str, str, str]:
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
        _, bucket, path = cls.aws_s3_parse_url(url)

        cfg = next(c for c in settings.LAMB_S3_CONFIG if c.bucket_name == bucket)
        s3_engine = S3Engine(config=cfg)
        s3_engine.delete_object(path)

    # properties
    @lazy_ro
    def _sync_client(self) -> S3Client:
        return self.construct_sync_client(self._config)

    @property
    def bucket_name(self) -> str | None:
        return self._config.bucket_name

    @property
    def bucket_url(self) -> str:
        if self._config.bucket_url:
            return self._config.bucket_url
        if self._config.region_name is not None:
            return f"https://s3.{self._config.region_name}.amazonaws.com/{self._config.bucket_name}/"
        return f"https://{self._config.bucket_name}.s3.amazonaws.com/"

    @property
    def endpoint_url(self) -> str | None:
        return self._config.endpoint_url

    # S3: object access urls
    def generate_presigned_url(
        self,
        path: str,
        expiration: int = 600,
        patch_bucket_url: bool = True,
        client_method: str = "get_object",
    ) -> str:
        """
        Generates a presigned url to download a file - simple and blind do not even try check file exists
        :param path: path to a stored file
        :param expiration: expiration of link in seconds
        :param patch_bucket_url: patch final url with external bucket link or return endpoint_url/signature_host based link
        :raise: FileNotFoundError
        """
        response: str = self._sync_client.generate_presigned_url(
            ClientMethod=client_method,
            Params={"Bucket": self.bucket_name, "Key": path},
            ExpiresIn=expiration,
        )

        if patch_bucket_url:
            _url_bucket = furl.furl(self.bucket_url)

            res = furl.furl(response)
            res.scheme = _url_bucket.scheme
            res.netloc = _url_bucket.netloc
            path_segments = res.path.segments
            path_segments.pop(0)  # remove bucket
            path_segments = _url_bucket.path.segments + path_segments
            res.path.segments = path_segments
            response = res.url
            logger.debug(
                f"{self.__class__.__name__}. generate_presigned_url: bucket_url version patched with url={response}"
            )

        return response

    def generate_public_url(self, path: str) -> str:
        """
        Simple URL constructor without presigned logic - suitable for acl:public=True objects
        :param path: path to a stored file
        """
        if self.bucket_url is not None:
            result = furl.furl(self.bucket_url)
            result.path.add(path)
            return result.url
        else:
            result = furl.furl()
            result.scheme = "https"
            result.host = f"{self._config.bucket_name}.s3.amazonaws.com"
            result.path.add(path)
            return result.url


class S3Engine(S3EngineBase):
    _config: S3BucketConfig

    # properties wrappers
    @property
    def _client(self) -> S3Client:
        return self._sync_client

    # methods
    def put_object(
        self,
        body: BinaryIO | UploadedFile | TemporaryUploadedFile | IO | bytes,
        path: str,
        file_type: str | None = None,
        private: bool | None = False,
    ) -> str:
        """
        Uploads the file to S3

        :param body: binary object to upload
        :param path: path to store in
        :param file_type: file content type
        :param private: defines if to store as private file
        :return: MD5 hash of the file
        """
        logger.debug(
            f"{self.__class__.__name__}. Would try put_object file to S3: ACL={'private' if private else 'public-read'}"
        )
        path = path.removeprefix("/")
        if isinstance(body, TemporaryUploadedFile):
            with open(body.temporary_file_path(), "rb") as f:
                response: dict = self._client.put_object(
                    Bucket=self.bucket_name,
                    ACL="private" if private else "public-read",
                    Body=f,
                    Key=path,
                    ContentType=file_type or "",
                )
            logger.debug(f"{self.__class__.__name__}. Uploaded as TemporaryUploadedFile")
        elif isinstance(body, UploadedFile):
            response: dict = self._client.put_object(
                Bucket=self.bucket_name,
                ACL="private" if private else "public-read",
                Body=body.read(),
                Key=path,
                ContentType=file_type or "",
            )
            logger.debug(f"{self.__class__.__name__}. Uploaded as UploadedFile")
        else:
            response: dict = self._client.put_object(
                Bucket=self.bucket_name,
                ACL="private" if private else "public-read",
                Body=body,
                Key=path,
                ContentType=file_type or "",
            )
            logger.debug(f"{self.__class__.__name__}. Uploaded as plain")

        md5_hash: str = response.get("ETag", "").strip('"')
        return md5_hash

    def bulk_put_objects(self, data, private: bool = False) -> None:
        # TODO: test - blind adapted
        # TODO: convert to gather logic
        uploaded_paths: list[str] = []
        try:
            for obj in data:
                self._client.put_object(
                    Bucket=self.bucket_name,
                    ACL="private" if private else "public-read",
                    Body=obj.data,
                    Key=obj.path,
                    ContentType=obj.mime_type,
                )
                uploaded_paths.append(obj.path)
        except Exception:
            logger.exception("Exception has occurred while uploading files: uploaded files will be deleted")
            for path in uploaded_paths:
                self._client.delete_object(Bucket=self.bucket_name, Key=path)
                logger.debug(f"{path} has been deleted")

    def get_object(self, path: str, **kwargs):
        """ "
        :raise: FileNotFoundError
        """
        try:
            path = path.removeprefix("/")
            response: dict = self._client.get_object(Bucket=self.bucket_name, Key=path, **kwargs)
        except ClientError as e:
            try:
                if e.response["Error"]["Code"] in ["NoSuchKey", "404"]:
                    raise FileNotFoundError from e
                else:
                    raise
            except AttributeError, KeyError:
                raise e
        result = response["Body"].read()
        return result

    def delete_object(self, path: str, **kwargs):
        """
        Removes file from S3

        :param path: relative path to stored file
        """
        try:
            path = path.removeprefix("/")
            kwargs = compact(kwargs)
            self._client.delete_object(Bucket=self.bucket_name, Key=path, **kwargs)
        except ClientError as e:
            try:
                if e.response["Error"]["Code"] in ["NoSuchKey", "404"]:
                    raise FileNotFoundError from e
                else:
                    raise
            except AttributeError, KeyError:
                raise e

    def head_object(self, path: str, **kwargs) -> dict[str, Any]:
        """
        Request low-level HEAD info from S3 storage about object

        :param path: relative path to stored file
        :param kwargs: additional low level client kwargs
        :return: S3 HEAD info dict
        """
        # TODO: test - blind adapted
        try:
            relative_path = path.removeprefix("/")
            response: dict = self._client.head_object(Bucket=self.bucket_name, Key=relative_path, **kwargs)
            return response
        except ClientError as e:
            # Raise proper exception if the file does not exist
            try:
                logger.info(f"{self.__class__.__name__}. HEAD exception: {e.response}")
                if e.response["Error"]["Code"] == "404":
                    raise FileNotFoundError from e
                else:
                    raise
            except AttributeError, KeyError:
                raise e

    def head_object_hash(self, path: str) -> str:
        """
        Receives MD5 hash of the file (from "ETag" property)

        :param path: path to a stored file
        :raise: FileNotFoundError
        :raise: LookupError
        """
        response = self.head_object(path=path)
        try:
            md5_hash: str = response["ETag"].strip('"')
        except KeyError:
            raise LookupError("Unable to fetch file hash from received response")
        return md5_hash

    def object_exists(self, path: str) -> bool:
        """
        Returns True if the file exists, otherwise returns False
        The result here is based on the result of the Head request from object_hash method

        :param path: path to a stored file
        """
        # TODO: test - blind adapted
        try:
            self.head_object_hash(path)
        except FileNotFoundError:
            return False
        return True

    def generate_presigned_url(self, path: str, expires_in: int | None = 3600) -> str:
        """
        Generates pre-signed url for a stored in S3 file

        :param path: stored file relative path
        :param expires_in: interval of link expiry
        :return: pre-signed url
        """
        try:
            presigned_url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": path},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            raise exc.ExternalServiceError from e
        logger.debug(f"Generated S3 presigned URL: {presigned_url}")
        return presigned_url


class AsyncS3Engine(S3EngineBase):
    # _config: S3BucketConfig
    _external_client: AsyncS3Client | None = None
    _managed_client: AsyncS3Client | None = None

    # lifecycle
    def __init__(
        self,
        config: S3BucketConfig,
        client: AsyncS3Client | None = None,
    ):
        super().__init__(config=config)
        self._external_client = client

    async def __aenter__(self) -> Self:
        if self._external_client is not None:
            logger.debug(
                f"{self.__class__.__name__}. async context enter: uses external client -> self._managed_client skip"
            )
        else:
            logger.debug(
                f"{self.__class__.__name__}. async context enter: "
                f"no external client -> self._managed_client create and enter"
            )
            _aws_client_creator = self.construct_async_creator(self._config)
            self._managed_client = await _aws_client_creator.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._managed_client is not None:
            logger.info(
                f"{self.__class__.__name__}. async context exit: self._managed_client exists -> exit and destroy"
            )
            await self._managed_client.__aexit__(exc_type, exc_val, exc_tb)
            self._managed_client = None

    # builders
    @staticmethod
    def construct_async_creator(conn_cfg: S3BucketConfig) -> ClientCreatorContext[AsyncS3Client]:
        _boto_config: AioConfig = AioConfig(
            **compact(
                {
                    "signature_version": "s3v4",
                    "connect_timeout": conn_cfg.connect_timeout,
                    "read_timeout": conn_cfg.read_timeout,
                    "request_checksum_calculation": "WHEN_REQUIRED",
                    "response_checksum_validation": "WHEN_REQUIRED",
                }
            )
        )
        _aws_session: aioboto3.Session = aioboto3.Session(
            aws_access_key_id=conn_cfg.access_key,
            aws_secret_access_key=conn_cfg.secret_key,
        )
        result: ClientCreatorContext[S3Client] = _aws_session.client(
            service_name="s3",
            endpoint_url=conn_cfg.endpoint_url,
            region_name=conn_cfg.region_name,
            config=_boto_config,
        )

        return result

    # properties wrappers
    @property
    def _client(self) -> AsyncS3Client:
        return self._external_client or self._managed_client

    # S3: wrapper
    async def put_object(
        self,
        path: str,
        body: BinaryIO | UploadedFile | TemporaryUploadedFile | IO | bytes,
        file_type: str | None,
        private: bool | None = False,
    ) -> str:
        """
        Uploads the file to S3

        :param body: binary object to upload
        :param path: path to store in
        :param file_type: file content type
        :param private: defines if to store as private file
        :return: MD5 hash of the file
        """
        logger.info(
            f"{self.__class__.__name__}. Would try put_object file to S3: ACL={'private' if private else 'public-read'}"
        )
        if isinstance(body, TemporaryUploadedFile):
            async with aiofiles.open(body.temporary_file_path(), "rb") as f:
                response: dict = await self._client.put_object(
                    Bucket=self.bucket_name,
                    ACL="private" if private else "public-read",
                    Body=f,
                    Key=path,
                    ContentType=file_type or "",
                )
            logger.info(f"{self.__class__.__name__}. Uploaded as TemporaryUploadedFile")
        elif isinstance(body, UploadedFile):
            response: dict = await self._client.put_object(
                Bucket=self.bucket_name,
                ACL="private" if private else "public-read",
                Body=body.read(),
                Key=path,
                ContentType=file_type or "",
            )
            logger.info(f"{self.__class__.__name__}. Uploaded as UploadedFile")
        else:
            response: dict = await self._client.put_object(
                Bucket=self.bucket_name,
                ACL="private" if private else "public-read",
                Body=body,
                Key=path,
                ContentType=file_type or "",
            )
            logger.info(f"{self.__class__.__name__}. Uploaded as plain")

        md5_hash: str = response.get("ETag", "").strip('"')
        return md5_hash

    async def bulk_put_objects(self, data, private: bool = False) -> None:
        # TODO: test - blind adapted
        # TODO: convert to gather logic
        uploaded_paths: list[str] = []
        try:
            for obj in data:
                await self._client.put_object(
                    Bucket=self.bucket_name,
                    ACL="private" if private else "public-read",
                    Body=obj.data,
                    Key=obj.path,
                    ContentType=obj.mime_type,
                )
                uploaded_paths.append(obj.path)
        except Exception:
            logger.exception("Exception has occurred while uploading files: uploaded files will be deleted")
            for path in uploaded_paths:
                await self._client.delete_object(Bucket=self.bucket_name, Key=path)
                logger.debug(f"{path} has been deleted")

    async def get_object(self, path: str, **kwargs):
        """
        :raise: FileNotFoundError
        """
        # TODO: test - blind adapted
        try:
            path = path.removeprefix("/")
            response: dict = await self._client.get_object(Bucket=self.bucket_name, Key=path, **kwargs)
        except ClientError as e:
            try:
                if e.response["Error"]["Code"] in ["NoSuchKey", "404"]:
                    raise FileNotFoundError from e
                else:
                    raise
            except AttributeError, KeyError:
                raise e
        result = await response["Body"].read()
        return result

    async def delete_object(self, path: str, **kwargs):
        """
        Removes file from S3

        :param path: relative path to stored file
        """
        try:
            path = path.removeprefix("/")
            kwargs = compact(kwargs)
            await self._client.delete_object(Bucket=self.bucket_name, Key=path, **kwargs)
        except ClientError as e:
            try:
                if e.response["Error"]["Code"] in ["NoSuchKey", "404"]:
                    raise FileNotFoundError from e
                else:
                    raise
            except AttributeError, KeyError:
                raise e

    async def head_object(self, path: str, **kwargs) -> dict[str, Any]:
        """
        Request low-level HEAD info from S3 storage about object

        :param path: relative path to stored file
        :param kwargs: additional low level client kwargs
        :return: S3 HEAD info dict
        """
        # TODO: test - blind adapted
        try:
            path = path.removeprefix("/")
            response: dict = await self._client.head_object(Bucket=self.bucket_name, Key=path, **kwargs)
            return response
        except ClientError as e:
            # Raise proper exception if the file does not exist
            try:
                if e.response["Error"]["Code"] == "404":
                    raise FileNotFoundError
                else:
                    raise
            except AttributeError, KeyError:
                raise e

    async def head_object_hash(self, path: str) -> str:
        """
        Receives MD5 hash of the file (from "ETag" property)

        :param path: path to a stored file
        :raise: FileNotFoundError
        :raise: LookupError
        """
        response = await self.head_object(path=path)
        try:
            md5_hash: str = response["ETag"].strip('"')
        except KeyError:
            raise LookupError("Unable to fetch file hash from received response")
        return md5_hash

    async def object_exists(self, path: str) -> bool:
        """
        Returns True if the file exists, otherwise returns False
        The result here is based on the result of the Head request from object_hash method

        :param path: path to a stored file
        """
        # TODO: test - blind adapted
        try:
            await self.head_object_hash(path)
        except FileNotFoundError:
            return False
        return True
