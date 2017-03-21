__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

import os
from boto3.session import Session
from django.conf import settings

from lamb.rest.exceptions import ServerError, ExternalServiceError
from lamb.service.image.upload_service.abstract import ImageUploadServiceAbstract


class ImageUploadServiceAmazonS3(ImageUploadServiceAbstract):
    """ Subclass of ImageUploadServiceAbstract that know how to store files on amazon s3 server

    This class realize logic of storing data on amazon s3 server with provided bucket name. Images stored in JPEG format.
    """
    def __init__(self, bucket_name, *args, **kwargs):
        super(ImageUploadServiceAmazonS3, self).__init__(*args, **kwargs)
        session = Session(
            aws_access_key_id=settings.LAMB_AWS_ACCESS_KEY,
            aws_secret_access_key=settings.LAMB_AWS_SECRET_KEY
        )
        s3 = session.resource('s3')
        exist_buckets = [ b.name for b in s3.buckets.all() ]
        if bucket_name not in exist_buckets:
            raise ServerError('AWS bucket with given \'%s\' bucket name not exist' % bucket_name)
        self.bucket = s3.Bucket(bucket_name)

    def store_image(self, image, suffix=None, proposed_name=None):
        """ Concrete realization of storage file on amazon s3 server.

        :param image: Instance of image to be stored
        :type image: PIL.Image
        :param suffix: Will be added at end of generated file name, may be None
        :type suffix: unicode
        :param proposed_name: Recommended by other logic name
        :type proposed_name: unicode
        :return: URL of stored file or None if some problem occurred
        :rtype: unicode
        """
        file_name = proposed_name
        if file_name is None:
            file_name = self._generate_random_file_name()

        if suffix is not None and len(suffix) > 0:
            file_name = '%s_%s.jpg' % (file_name, suffix)
        else:
            file_name = '%s.jpg' % file_name

        temp_file = os.path.join(settings.LAMB_STATIC_FOLDER, file_name)
        image.save(temp_file, 'JPEG', quality=settings.LAMB_IMAGE_UPLOAD_QUALITY)

        # TODO: Change to load file in memory
        try:
            self.bucket.put_object(Key=file_name, Body=open(temp_file, 'rb'), ACL='public-read', ContentType='image/jpeg')
            uploaded_url = "http://%s.s3.amazonaws.com/%s" % (self.bucket.name, file_name)
            return uploaded_url
        except Exception as e:
            print e.__class__.__name__, e
            raise ExternalServiceError('Could not load data in bucket')
        finally:
            os.remove(temp_file)
