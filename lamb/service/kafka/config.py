from __future__ import annotations

import dataclasses
from typing import List, Optional

from lamb.utils.transformers import tf_list_string

# Lamb Framework
from lamb.utils.validators import v_opt_string

__all__ = ["KafkaConfig"]


@dataclasses.dataclass
class KafkaConfig:
    bootstrap_servers: List[str]
    security_protocol: Optional[str] = None
    sasl_mechanism: Optional[str] = None
    sasl_plain_username: Optional[str] = None
    sasl_plain_password: Optional[str] = None

    def __post_init__(self):
        self.bootstrap_servers = tf_list_string(self.bootstrap_servers)
        self.sasl_plain_username = v_opt_string(self.sasl_plain_username)
        self.sasl_plain_password = v_opt_string(self.sasl_plain_password)
        self.security_protocol = v_opt_string(self.security_protocol)
        self.sasl_mechanism = v_opt_string(self.sasl_mechanism)
