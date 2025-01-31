from __future__ import annotations

import dataclasses
from typing import Optional

from lamb.utils.transformers import tf_list_string
from lamb.utils.validators import validate_not_empty

__all__ = ["Endpoint"]


@dataclasses.dataclass
class Endpoint:
    app_name: str
    url_name: str
    http_methods: Optional[str] = None

    def __post_init__(self):
        self.app_name = validate_not_empty(self.app_name)
        self.url_name = validate_not_empty(self.url_name)
        _http_methods = tf_list_string(self.http_methods)
        self.http_methods = _http_methods
