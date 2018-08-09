# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


import uuid
import logging
from PIL import Image
from django.conf import settings

from lamb.service.image.model import LambImage
from lamb.exc import InvalidParamTypeError, ServerError

logger = logging.getLogger(__name__)


class ImageUploadServiceAbstract(object):
    """ Abstract class for engine that can store images

    Attributes:

        source_file (str): Path to source file that will be processed by engine
        thumb_size (int): Size for thumbnail copy of image,
            image will be re-sized to fit (thumb_size, shumb_size) by aspect ratio mode.
            By default have value 100px
        small_size (int): Size for small copy of image,
            image will be re-sized to fit (small_size, small_size) by aspect ratio mode.
            By default have value 200px.
        middle_size (int): Size for middle copy of image,
            image will be re-sized to fit (middle_size, middle_size) by aspect ratio mode.
            By default have value 400px.
        large_size (int): Size for large copy of image,
            image will be re-sized to fit (large_size, large_size) by aspect ratio mode.
            By default have value 800px.
    """
    def __init__(self,
                 source_file,
                 thumb_size=settings.LAMB_IMAGE_SIZE_THUMBNAIL,
                 small_size=settings.LAMB_IMAGE_SIZE_SMALL,
                 middle_size=settings.LAMB_IMAGE_SIZE_MEDIUM,
                 large_size=settings.LAMB_IMAGE_SIZE_LARGE
                 ):
        self.source_file = source_file
        self.thumb_size = thumb_size
        self.small_size = small_size
        self.middle_size = middle_size
        self.large_size = large_size

    def _generate_random_file_name(self):
        return str(uuid.uuid4())

    def process_image(self, image_class=LambImage):
        """ Process image file provided in constructor

        Will do several things for image loaded from ``self.source_file``

            1. Load original image in memory
            2. For each resolution (thumb, small, middle, large, original) will prepare corresponding image and try to save it with ``self.store_image()`` method

        :param image_class: Class object for creating instance, should be subclass of ``LambImage``.
         If not provided ``LambImage`` used by default.
        :type image_class: class
        :return: Instance of processed ``LambImage`` (or subclass if class provided) with filled URLs for all resolutions
        :rtype: LambImage

        """
        def _process_size(source_image, size, suffix, proposed_name):
            """
            :type source_image: PIL.Image
            :type size: int, None
            :type suffix: unicode
            :type proposed_name: unicode
            :rtype: unicode
            """
            # create copy if size known
            image_copy = source_image.copy()
            if size is not None:
                image_copy.thumbnail((size, size), Image.ANTIALIAS)

            # create suffix
            suffix_components = list()
            if suffix is not None:
                suffix_components.append(suffix)
            if size is not None:
                suffix_components.append('x%d' % size)
            if len(suffix_components) > 0:
                suffix = '_'.join(suffix_components)

            return self.store_image(image_copy, suffix, proposed_name)

        # Get original image
        try:
            src = Image.open(self.source_file)
        except IOError as e:
            raise InvalidParamTypeError("Could not open file as image")
        except Exception as e:
            logger.error('Failed to read image from file: %s' % e)
            raise ServerError("Unhandled open image error")

        src = src.convert('RGB')
        # store data
        proposed_name = self._generate_random_file_name()
        result = image_class()
        result.original_url = _process_size(src, None, 'orig', proposed_name)
        result.thumb_url = _process_size(src, self.thumb_size, 'thumb', proposed_name)
        result.small_url = _process_size(src, self.small_size, 'small', proposed_name)
        result.middle_url = _process_size(src, self.middle_size, 'middle', proposed_name)
        result.large_url = _process_size(src, self.large_size, 'large', proposed_name)

        return result

    def store_image(self, image, suffix=None, proposed_name=None):
        """ Abstract method for processing concrete file

        warning:
        Pure abstract method, should be realized in concrete subclass with corresponding store logic.
        Should generate unique name for file, append provided suffix before file extension and store it.

        :param image: Instance of image to be stored
        :type image: PIL.Image
        :param suffix: Will be added at end of generated file name, may be None
        :type suffix: unicode
        :param proposed_name: Recommended by other logic name
        :type proposed_name: unicode
        :return: URL of stored file or None if some problem occurred
        :rtype: unicode
        """
        raise NotImplementedError('Store_image method is abstract, should be realized in subclass')
