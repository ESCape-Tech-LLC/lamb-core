# -*- coding: utf-8 -*-

import logging
from typing import List, Type, Optional

from django.conf import settings

from lamb.exc import ServerError
from lamb.utils import LambRequest, import_by_name

from .types import ImageUploadSlice
from .base import BaseUploader
from ..model import AbstractImage

logger = logging.getLogger(__name__)

__all__ = ['get_default_uploader_class', 'upload_images']


def get_default_uploader_class() -> Type[BaseUploader]:
    """
    Load module for image uploading.

    :return: Imported uploader class.
    """
    logger.info('Image uploader created: %s' % settings.LAMB_IMAGE_UPLOAD_ENGINE)
    result = import_by_name(settings.LAMB_IMAGE_UPLOAD_ENGINE)
    if not issubclass(result, BaseUploader):
        raise ServerError('Improperly configured image uploader')
    return result


def upload_images(request: LambRequest,
                  slicing: List[ImageUploadSlice],
                  image_class: Type[AbstractImage],
                  envelope_folder: Optional[str] = None,
                  limit: Optional[int] = None,
                  uploader_class: Optional[Type[BaseUploader]] = None) -> List[AbstractImage]:
    """
    Uploads image from request to project storage.

    :param request: Request
    :param uploader_class: Uploader engine class
    :param slicing: Images sizes configuration
    :param image_class: Instances class for result
    :param envelope_folder: Destination subfolder inside storage
    :param limit: Upload images count limit

    :return: List of Image model instances.
    """
    # upload images
    if uploader_class is None:
        uploader_class = get_default_uploader_class()

    uploader = uploader_class(envelope_folder=envelope_folder)
    stored_slices = uploader.process_request(
        request=request,
        slicing=slicing,
        required_count=limit
    )
    # store images info
    result = list()
    for ss in stored_slices:
        image = image_class()
        image.slices_info = ss
        result.append(image)
    return result
