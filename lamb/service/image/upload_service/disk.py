# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


import os

from urllib.parse import urljoin
from django.conf import settings

from lamb.service.image.upload_service.abstract import ImageUploadServiceAbstract


class ImageUploadServiceDisk(ImageUploadServiceAbstract):
    """ Subclass of ImageUploadServiceAbstract that know how to store files on local server in static folder

    This class realize logic of storing data on disk in provided folder. Images stored in JPEG format.

    Attributes:

        storage_dir (str): Path to folder where we need to store images
        static_url (str): Base part of URL for images, final path will be constructed as <base_url>/<generated_name>.
            For example if static_url=`http://127.0.0.1:8000/static/` then final image can have url
            `http://127.0.0.1:8000/static/`
    """

    def __init__(self, storage_dir='', static_url='', *args, **kwargs):
        """ Naive constructor

        Raises:
            ValueError: If provided storage_dir is not exist or is not folder.
        """
        super(ImageUploadServiceDisk, self).__init__(*args, **kwargs)
        if not os.path.isdir(storage_dir):
            raise ValueError('Provided storage dir is not exist')
        self.storage_dir = storage_dir
        self.static_url = static_url

    def store_image(self, image, suffix=None, proposed_name=None):
        """ Concrete realization of storage file on disk.

        Try to do next:

            1. Generate random name by sha256(uuid.uuid4().bytes).hexdigest()
            2. Append to this name suffix if provided
            3. Append file extension `.jpg`
            4. Check is file with this name exist on disk - may exist in case of collision error

        Totally will make 10 attempts to make this and raise empty OSError if not success

        If proposed name provided try to save with this name, but if failed return to random generation logic.

        :param image: Instance of image to be stored
        :type image: PIL.Image
        :param suffix: Will be added at end of generated file name, may be None
        :type suffix: unicode
        :param proposed_name: Recommended by other logic name
        :type proposed_name: unicode
        :return: URL of stored file or None if some problem occurred
        :rtype: unicode
        """
        attempts = 10
        while attempts > 0:
            file_name = proposed_name
            if proposed_name is None:
                file_name = self._generate_random_file_name()

            if suffix is not None and len(suffix) > 0:
                file_name = '%s_%s.jpg' % (file_name, suffix)
            else:
                file_name = '%s.jpg' % file_name
            full_path = os.path.join(self.storage_dir, file_name)

            if not os.path.exists(full_path):
                image.save(full_path, 'JPEG', quality=settings.LAMB_IMAGE_UPLOAD_QUALITY)
                return urljoin(self.static_url, file_name)
            proposed_name = None  # nullify recommend name in case of have not save image
            attempts -= 1
        raise OSError
