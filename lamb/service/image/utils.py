from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple, Type
from urllib.parse import urljoin

from django.conf import settings

# Lamb Framework
from lamb.exc import ServerError
from lamb.service.aws.s3 import S3Uploader
from lamb.types import IT, SliceRule
from lamb.utils import LambRequest

from ...utils.core import import_by_name
from .model import AbstractImage
from .uploaders import BaseUploader

logger = logging.getLogger(__name__)


__all__ = [
    "get_default_uploader_class",
    "create_image_slices",
    "upload_images",
    "parse_static_url",
    "remove_image_from_storage",
]


def get_default_uploader_class() -> Type[BaseUploader]:
    """
    Load module for image uploading.

    :return: Imported uploader class.
    """
    logger.info("Image uploader created: %s" % settings.LAMB_IMAGE_UPLOAD_ENGINE)
    result = import_by_name(settings.LAMB_IMAGE_UPLOAD_ENGINE)
    if not issubclass(result, BaseUploader):
        raise ServerError("Improperly configured image uploader")
    return result


def create_image_slices(
    request: LambRequest,
    slicing: List[SliceRule],
    envelope_folder: Optional[str] = None,
    limit: Optional[int] = None,
    uploader_class: Optional[Type[BaseUploader]] = None,
    allow_svg: Optional[bool] = False,
) -> List[List[IT]]:
    """
    Uploads images from request and generates slices.

    :param request: Request
    :param uploader_class: Uploader engine class
    :param slicing: Images sizes configuration
    :param envelope_folder: Destination subfolder inside storage
    :param limit: Upload images count limit
    :param allow_svg: Flag to allow/disallow svg upload

    :return: List of stored slices.
    """
    # upload images
    if uploader_class is None:
        uploader_class = get_default_uploader_class()

    uploader = uploader_class(envelope_folder=envelope_folder)
    stored_slices = uploader.process_request(
        request=request, slicing=slicing, required_count=limit, allow_svg=allow_svg
    )
    return stored_slices


def upload_images(
    request: LambRequest,
    slicing: List[SliceRule],
    image_class: Type[AbstractImage],
    envelope_folder: Optional[str] = None,
    limit: Optional[int] = None,
    uploader_class: Optional[Type[BaseUploader]] = None,
    allow_svg: Optional[bool] = False,
) -> List[AbstractImage]:
    """
    Uploads image from request to project storage.

    :param request: Request
    :param uploader_class: Uploader engine class
    :param slicing: Images sizes configuration
    :param image_class: Instances class for result
    :param envelope_folder: Destination subfolder inside storage
    :param limit: Upload images count limit
    :param allow_svg: Flag to allow/disallow svg upload

    :return: List of Image model instances.
    """
    stored_slices = create_image_slices(
        request=request,
        slicing=slicing,
        envelope_folder=envelope_folder,
        limit=limit,
        uploader_class=uploader_class,
        allow_svg=allow_svg,
    )
    # Create images of specified class
    result = list()
    for ss in stored_slices:
        image = image_class()
        image.slices_info = ss
        result.append(image)
    return result


def parse_static_url(url: str) -> Tuple[str, str]:
    """
    :return: Tuple of relative path and full path to static file
    """

    # Get static url and folder
    try:
        static_url = settings.LAMB_STATIC_URL
    except AttributeError:
        host = settings.HOST
        if settings.PORT not in [80, 443]:
            host = f"{host}:{settings.PORT}"
        static_url = urljoin(f"{settings.SCHEME}://{host}", "static")

    try:
        static_folder = settings.LAMB_STATIC_FOLDER
    except AttributeError:
        static_folder = os.path.join(settings.BASE_DIR, "static")

    # Check for match
    if not url.startswith(static_url):
        raise ValueError("No static url match found")

    # Parse relative path
    static_url_len = len(static_url)
    if not static_url.endswith("/"):
        static_url_len += 1
    relative_path = url[static_url_len:]

    return relative_path, os.path.join(static_folder, relative_path)


def remove_image_from_storage(image: AbstractImage, fail_silently: Optional[bool] = True):
    """
    Removes all slices of an image from storage.
    Supports slices that were uploaded using ImageUploadServiceDisk and ImageUploadServiceAmazonS3

    :param image: Image object
    :param fail_silently: If set to False, raises an exception on any error
    """
    logger.debug(f"Removing image file from storage: image_id={image.image_id}")
    for slice_info in image.slices_info:
        # Try to find and remove local file
        file_path = None
        try:
            file_path = parse_static_url(slice_info.url)[1]
        except ValueError:
            logger.debug(f"No static path found for url: {slice_info.url}")
        if file_path:
            try:
                os.remove(file_path)
            except Exception:
                if not fail_silently:
                    raise
            continue

        # Else try to find and remove S3 file
        try:
            S3Uploader.remove_by_url(slice_info.url)
        except Exception:
            if not fail_silently:
                raise

    logger.debug("Successfully finished removing image file from storage")
