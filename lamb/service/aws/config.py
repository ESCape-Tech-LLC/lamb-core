from __future__ import annotations

import dataclasses
import json

from lamb.json.mixins import ResponseEncodableMixin
from lamb.utils import masked_dict


@dataclasses.dataclass
class S3BucketConfig(ResponseEncodableMixin):
    """
    Notes:
        - arg `bucket_url` desired for calculating external link to file.
        - arg `signature_host` desired for cases when app->S3 communication endpoint url differs from balancer->S3 host
    """

    # S3 params
    bucket_name: str | None = None
    region_name: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    endpoint_url: str | None = None
    connect_timeout: float | None = None
    read_timeout: float | None = None
    # deprecated
    check_buckets_list: bool = False

    # wrapper params
    bucket_url: str | None = None
    signature_host: str | None = None

    def response_encode(self, request=None) -> dict:
        result = dataclasses.asdict(self)
        result = masked_dict(result, "access_key", "secret_key")
        return result

    def __str__(self):
        return json.dumps(self.response_encode())

    def __repr__(self):
        return json.dumps(self.response_encode())
