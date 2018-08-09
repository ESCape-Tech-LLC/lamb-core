# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


from .model import LambImage
from .upload_service.disk import ImageUploadServiceDisk
from .upload_service.amazon_s3 import ImageUploadServiceAmazonS3

__all__ = [
    'LambImage', 'ImageUploadServiceAmazonS3', 'ImageUploadServiceDisk'
]
