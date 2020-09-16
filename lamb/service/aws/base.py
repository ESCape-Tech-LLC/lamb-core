# -*- coding: utf-8 -*-

from typing import Optional
from django.conf import settings
from boto3.session import Session as AWSSession

__all__ = ['AWSBase']


class AWSBase:

    def __init__(self,
                 aws_access_key_id: Optional[str] = settings.LAMB_AWS_ACCESS_KEY,
                 aws_secret_access_key: Optional[str] = settings.LAMB_AWS_SECRET_KEY,
                 *args,
                 **kwargs):

        # Create session
        self._aws_session = AWSSession(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
