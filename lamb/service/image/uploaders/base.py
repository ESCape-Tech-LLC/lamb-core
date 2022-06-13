from __future__ import annotations

import os
import uuid
import base64
import logging
from io import BytesIO
from typing import List, Type, Union, Iterable, Optional

from django.core.files.uploadedfile import SimpleUploadedFile

# Lamb Framework
from lamb import exc
from lamb.utils import LambRequest, compact, file_is_svg
from lamb.types.image import IT, Mode, SliceRule, ImageSlice

from PIL import Image as PILImage

logger = logging.getLogger(__name__)


__all__ = ["BaseUploader"]


def _is_base64(sb) -> bool:
    try:
        if type(sb) == str:
            # If there's any unicode here, an exception will be thrown and the function will return false
            sb_bytes = bytes(sb, "ascii")
        elif type(sb) == bytes:
            sb_bytes = sb
        else:
            raise exc.InvalidParamTypeError("Argument must be string or bytes")
        return base64.b64encode(base64.b64decode(sb_bytes)) == sb_bytes
    except Exception:
        return False


def _get_bytes_image_mime_type(data: bytes) -> Optional[str]:
    try:
        stream = BytesIO(data)

        image = PILImage.open(stream)
        image.verify()
        return PILImage.MIME[image.format]
    except Exception as e:
        logger.debug(f"image encoded check exception: {e}")
        return None


class BaseUploader(object):
    def __init__(self, envelope_folder: str = None) -> None:
        super().__init__()
        self.enveloper_folder = envelope_folder

    def construct_relative_path(self, proposed_file_name: str) -> str:
        path_components = compact([self.enveloper_folder, proposed_file_name])
        result = os.path.join(*path_components)
        return result

    def process_image(
        self,
        source_image: Union[PILImage.Image, str, BytesIO],
        request: LambRequest,
        slices: Iterable[SliceRule] = (),
        image_format: Optional[str] = None,
        allow_svg: Optional[bool] = False,
        slice_class: Type[IT] = ImageSlice,
    ) -> List[IT]:
        """
        Processes single image

        :param source_image: PIL Image, file path, or bytes
        :param request: Request
        :param slices: Slicing configuration
        :param image_format: Optional image format to override
        :param allow_svg: Flag to allow/disallow svg upload
        :param slice_class: support for special slicing class

        :return: List of uploaded slices info's
        """

        is_svg = False
        try:
            if isinstance(source_image, PILImage.Image):
                src = source_image
            else:
                src = PILImage.open(source_image)
        except IOError as e:
            if allow_svg:
                # Seek to 0 if bytes and check if svg file
                try:
                    source_image.seek(0)
                except AttributeError:
                    pass
                is_svg = file_is_svg(source_image)
            if not is_svg:
                raise exc.InvalidParamTypeError("Could not open file as valid image") from e
        except Exception as e:
            logger.exception(e)
            raise exc.ServerError("Failed to process file as image") from e

        # store data
        filename_base = str(uuid.uuid4())
        image_format = "svg" if is_svg else image_format or src.format
        filename_extension = image_format.lower()

        if is_svg:
            proposed_file_name = f"{filename_base}.{filename_extension}"
            image_url = self.store_image(
                image=source_image, proposed_file_name=proposed_file_name, request=request, image_format=image_format
            )
            result = [slice_class(title=s.title, mode=None, url=image_url, width=None, height=None) for s in slices]
        else:
            result = list()

            for s in slices:
                # create copy if size known
                image_copy = src.copy()

                # modify according to s config
                if s.mode == Mode.Resize:
                    image_copy.thumbnail((s.side, s.side), PILImage.ANTIALIAS)
                elif s.mode == Mode.Crop:
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
                filename = "_".join(pc for pc in (filename_base, s.suffix) if pc is not None and len(pc))
                proposed_file_name = f"{filename}.{filename_extension}"

                # store info about new slice
                image_url = self.store_image(
                    image=image_copy, proposed_file_name=proposed_file_name, request=request, image_format=image_format
                )

                result.append(
                    slice_class(
                        title=s.title, mode=s.mode, url=image_url, width=image_copy.size[0], height=image_copy.size[1]
                    )
                )

        return result

    def process_request(
        self,
        request: LambRequest,
        slicing: Iterable[SliceRule] = (),
        required_count: Optional[int] = None,
        image_format: Optional[str] = None,
        allow_svg: Optional[bool] = False,
        slice_class: Type[IT] = ImageSlice,
    ) -> List[List[IT]]:
        """
        Performs uploading of request's image files.

        :param request: Request
        :param slicing: Slicing configuration
        :param required_count: Count of images that should be in request
        :param image_format: Optional image format to override
        :param allow_svg: Flag to allow/disallow svg upload
        :param slice_class: support for special slicing class

        :return: List of uploaded slices info's collection for each image.
        """
        # try to decode image stored as base64 fields
        files = request.FILES.copy()
        for key, value in request.POST.items():
            try:
                if not _is_base64(value):
                    continue
                # TODO: migrate to core utils
                data = base64.b64decode(value)
                logger.info(f"{key} -> {value} -> {data}")

                # TODO: migrate to core and rename to  all file kinds
                mime_type = _get_bytes_image_mime_type(data)
                if mime_type is None:
                    continue
                logger.debug(f"encoded image mime-type: {mime_type}")

                f = SimpleUploadedFile(key, data, content_type=mime_type)
                files[key] = f
                logger.debug("did patch FILES object to include image from POST base64 encoded data")
            except Exception:
                continue

        # check request
        if len(files) == 0:
            raise exc.InvalidBodyStructureError("Uploading image is missing")
        if required_count is not None:
            if not isinstance(required_count, int):
                logger.warning("Invalid data type received for required_count = %s" % required_count)
                raise exc.ServerError("Improperly configured uploader")
            if len(files) != required_count:
                raise exc.InvalidBodyStructureError("Invalid count of uploading images")

        # Decode original image
        result = list()
        for _, uploaded_file in files.items():
            processed_image_slices = self.process_image(
                source_image=uploaded_file,
                slices=slicing,
                request=request,
                image_format=image_format,
                allow_svg=allow_svg,
                slice_class=slice_class,
            )
            result.append(processed_image_slices)

        return result

    def store_image(
        self, image: PILImage.Image, proposed_file_name: str, request: LambRequest, image_format: Optional[str] = None
    ) -> str:
        """
        Implements specific storage logic

        :return: URL of stored image
        """
        raise exc.ServerError("Abstract image upload service does not realize store image logic")
