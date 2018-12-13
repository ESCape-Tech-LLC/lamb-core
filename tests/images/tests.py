from boto3 import Session
from django.test.client import Client
from django.test.utils import override_settings

from moto import mock_s3

from lamb.db.context import lamb_db_context
from tests.testcases import LambTestCase

from .model import SimpleImage


@override_settings(ROOT_URLCONF='tests.images.urls')
@override_settings(LAMB_IMAGE_UPLOAD_ENGINE='lamb.service.image.uploaders.ImageUploadServiceDisk')
class ImagesDiskTest(LambTestCase):
    def setUp(self):
        with lamb_db_context() as session:
            session.query(SimpleImage).delete()

    def test_retrieve(self):
        client = Client()
        result = client.get('/simple_images/')
        self.assertEquals(result.status_code, 200)
        data = self.get_json(result)
        self.assertEqual(len(data), 0)

    def test_upload(self):
        client = Client()
        f1 = open('tests/images/files/image_portrait.jpeg', 'rb')
        f2 = open('tests/images/files/image_square.jpeg', 'rb')
        f3 = open('tests/images/files/image_landscape.jpg', 'rb')
        result = client.post('/simple_images/', {'attachment': f1,
                                                 'attachment2': f2,
                                                 'attachment3': f3})
        self.assertEquals(result.status_code, 201)
        result = client.get('/simple_images/')
        self.assertEquals(result.status_code, 200)
        data = self.get_json(result)
        self.assertEqual(len(data), 3)


@override_settings(ROOT_URLCONF='tests.images.urls')
@override_settings(LAMB_IMAGE_UPLOAD_ENGINE='lamb.service.image.uploaders.ImageUploadServiceAmazonS3')
@mock_s3
class ImagesAwsTest(LambTestCase):
    def setUp(self):
        from django.conf import settings
        with lamb_db_context() as session:
            session.query(SimpleImage).delete()
        self.aws_session = Session(
            aws_access_key_id=settings.LAMB_AWS_ACCESS_KEY,
            aws_secret_access_key=settings.LAMB_AWS_SECRET_KEY
        )
        s3 = self.aws_session.resource('s3')
        s3.create_bucket(Bucket=settings.LAMB_AWS_BUCKET_NAME)

    def test_retrieve(self):
        client = Client()
        result = client.get('/simple_images/')
        self.assertEquals(result.status_code, 200)
        data = self.get_json(result)
        self.assertEqual(len(data), 0)

    def test_upload(self):
        client = Client()
        f1 = open('tests/images/files/test.png', 'rb')
        f2 = open('tests/images/files/image_square.jpeg', 'rb')
        result = client.post('/simple_images/', {'attachment': f1, 'attachment2': f2})
        self.assertEquals(result.status_code, 201)
        result = client.get('/simple_images/')
        self.assertEquals(result.status_code, 200)
        data = self.get_json(result)
        self.assertEqual(len(data), 2)  # Check uploaded 2 images
        self.assertEqual(len(data[0]['slices_info']), 3)  # And have 3 slices
