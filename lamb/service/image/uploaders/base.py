# -*- coding: utf-8 -*-

import os
import uuid
import logging
from typing import List, Iterable, Union, Optional
from dataclasses import asdict
from PIL import Image as PILImage

from lamb.utils import compact, LambRequest
from lamb import exc

from .types import ImageUploadMode, ImageUploadSlice, UploadedSlice

logger = logging.getLogger(__name__)

__all__ = ['BaseUploader']


class BaseUploader(object):
    def __init__(self, envelope_folder: str = None) -> None:
        super().__init__()
        self.enveloper_folder = envelope_folder

    def construct_relative_path(self, proposed_file_name: str) -> str:
        path_components = compact([
            self.enveloper_folder,
            proposed_file_name
        ])
        result = os.path.join(*path_components)
        return result

    def process_image(self, source_image: Union[PILImage.Image, str],
                      request: LambRequest,
                      slices: Iterable[ImageUploadSlice] = ()) -> List[dict]:
        """
        Processes single images
        :param source_image: PIL Image or file
        :param request: Request
        :param slices: Slicing configuration
        :return: List of uploaded slices info's
        """
        try:
            if isinstance(source_image, PILImage.Image):
                src = source_image
            else:
                src = PILImage.open(source_image)
        except IOError as e:
            raise exc.InvalidParamTypeError('Could not open file as valid image') from e
        except Exception as e:
            logger.exception(e)
            raise exc.ServerError('Failed to process file as image') from e

        # store data
        filename_base = str(uuid.uuid4())
        filename_extension = src.format.lower()
        result = list()

        for s in slices:
            # create copy if size known
            image_copy = src.copy()

            # modify according to s config
            if s.mode == ImageUploadMode.Resize:
                image_copy.thumbnail((s.side, s.side), PILImage.ANTIALIAS)
            elif s.mode == ImageUploadMode.Crop:
                shortest = min(image_copy.size)
                left = (image_copy.size[0] - shortest) / 2
                top = (image_copy.size[1] - shortest) / 2
                right = image_copy.size[0] - left
                bottom = image_copy.size[1] - top
                image_copy = image_copy.crop((left, top, right, bottom))
                image_copy.thumbnail((s.side, s.side), PILImage.ANTIALIAS)

            # hack to save image format
            image_copy.format = src.format

            # prepare file name
            filename = '_'.join(pc for pc in (filename_base, s.suffix)
                                if pc is not None and len(pc))
            proposed_file_name = f'{filename}.{filename_extension}'

            # store info about new slice
            image_url = self.store_image(image_copy, proposed_file_name, request)

            result.append(
                asdict(UploadedSlice(s.title, s.mode.value, image_url, image_copy.size[0], image_copy.size[1])))

        return result

    def process_request(self, request: LambRequest,
                        slicing: Iterable[ImageUploadSlice] = (),
                        required_count: Optional[int] = None) -> List[List[dict]]:
        """
        Performs uploading of request's image files.
        :param request: Request
        :param slicing: Slicing configuration
        :param required_count: Count of images that should be in request
        :return: List of uploaded slices info's collection for each image.
        """
        # check request
        if len(request.FILES) == 0:
            raise exc.InvalidBodyStructureError('Uploading image missed')
        if required_count is not None:
            if not isinstance(required_count, int):
                logger.warning('Invalid data type received for required_count = %s' % required_count)
                raise exc.ServerError('Improperly configured uploader')
            if len(request.FILES) != required_count:
                raise exc.InvalidBodyStructureError('Invalid count of uploading images')

        # Decode original image
        result = list()
        for _, uploaded_file in request.FILES.items():
            processed_image_slices = self.process_image(
                source_image=uploaded_file,
                slices=slicing,
                request=request
            )
            result.append(processed_image_slices)

        return result

    def store_image(self, image: PILImage.Image,
                    proposed_file_name: str,
                    request: LambRequest) -> str:
        """ Implements specific storage logic
        :return: URL of stored image
        """
        raise exc.ServerError('Abstract image upload service doesn\'t realize store image logic')
