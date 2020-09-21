# -*- coding: utf-8 -*-

from .base import BaseUploader
from .disk import ImageUploadServiceDisk
from .s3 import ImageUploadServiceAmazonS3
from .types import ImageUploadMode, ImageUploadSlice

__all__ = ['BaseUploader', 'ImageUploadServiceDisk', 'ImageUploadServiceAmazonS3',
           'ImageUploadMode', 'ImageUploadSlice']
