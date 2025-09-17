from __future__ import annotations

from boto3.session import Session as AWSSession
from django.conf import settings

__all__ = ["AWSBase"]


class AWSBase:
    def __init__(self, aws_access_key_id: str | None = None, aws_secret_access_key: str | None = None, *args, **kwargs):
        # inject default
        aws_access_key_id = aws_access_key_id or settings.LAMB_AWS_ACCESS_KEY
        aws_secret_access_key = aws_secret_access_key or settings.LAMB_AWS_SECRET_KEY

        # Create session
        self._aws_session = AWSSession(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
