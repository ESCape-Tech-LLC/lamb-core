# Lamb Framework

from .model import ImageMixin, AbstractImage
from .utils import (
    upload_images,
    parse_static_url,
    create_image_slices,
    remove_image_from_storage,
    get_default_uploader_class,
)
from .uploaders import BaseUploader, ImageUploadServiceDisk, ImageUploadServiceAmazonS3
