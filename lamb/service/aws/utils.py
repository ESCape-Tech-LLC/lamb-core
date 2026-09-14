import logging
import pathlib

import aiofiles
import furl
from django.conf import settings

from lamb.exc import InvalidParamValueError
from lamb.service.aws.config import S3BucketConfig
from lamb.service.aws.s3engine import AsyncS3Engine, S3Engine

__all__ = ["s3_download_file_async", "s3_download_file_sync", "s3_filepath_parse"]

logger = logging.getLogger(__name__)


def s3_filepath_parse(s3_file_path: str | furl.furl) -> tuple[furl.furl, S3BucketConfig]:
    """Parser of S3 file descriptions

    Expects that file_path looks like s3://<bucket>/<path>.
    Would try to discover S3 config within settings.LAMB_S3_CONFIG
    and return path converted to furl.furl object and relevant S3BucketConfig
    """
    if isinstance(s3_file_path, str):
        s3_file_url = furl.furl(s3_file_path)
    elif isinstance(s3_file_path, furl.furl):
        s3_file_url = s3_file_path
    else:
        raise InvalidParamValueError(f"Unknown S3 file path: {s3_file_path}")

    if s3_file_url.scheme != "s3":
        raise InvalidParamValueError("Invalid S3 URL")

    s3_cfg: S3BucketConfig = settings.LAMB_S3_CONFIG.get(s3_file_url.netloc, None)
    if s3_cfg is None:
        raise InvalidParamValueError(f"Unknown S3 bucket: {s3_file_url.netloc}")

    return s3_file_url, s3_cfg


def s3_download_file_sync(s3_file_path: str, output_file_path: str | pathlib.Path | None = None):
    """Download file from S3 description in sync manner"""
    # parse arguments
    s3_file_url, s3_cfg = s3_filepath_parse(s3_file_path)
    output_file_path = output_file_path or pathlib.Path(str(s3_file_url.path)).name
    logger.info(f"s3_download_file_sync. start downloading: {s3_file_url.url} -> {output_file_path=}")

    # download file
    engine: S3Engine = S3Engine(config=s3_cfg)
    file_data = engine.get_object(path=str(s3_file_url.path))
    logger.debug(f"s3_download_file_sync. received content: [bytes={len(file_data)}] {file_data[:100]}...")
    with open(output_file_path, "wb") as f:
        f.write(file_data)

    logger.info(f"s3_download_file_sync. did download: {s3_file_url.url} -> {output_file_path=}")


async def s3_download_file_async(s3_file_path: str, output_file_path: str | pathlib.Path | None = None):
    """Download file from S3 description in async manner"""
    # parse arguments
    s3_file_url, s3_cfg = s3_filepath_parse(s3_file_path)
    output_file_path = output_file_path or pathlib.Path(str(s3_file_url.path)).name

    logger.info(f"s3_download_file_async. start downloading: {s3_file_url.url} -> {output_file_path=}")

    # download file
    async with AsyncS3Engine(config=s3_cfg) as engine:
        file_data = await engine.get_object(path=str(s3_file_url.path))
        logger.debug(f"s3_download_file_async. received content: [bytes={len(file_data)}] {file_data[:100]}...")
        async with aiofiles.open(output_file_path, "wb") as f:
            await f.write(file_data)

    logger.info(f"s3_download_file_async. did download: {s3_file_url.url} -> {output_file_path=}")
