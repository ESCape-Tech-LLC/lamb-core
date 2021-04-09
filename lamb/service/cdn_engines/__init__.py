from typing import Dict, Type

from .base import BaseCDNEngine
from .cloud_front import CloudFrontCDNEngine

__all__ = ['BaseCDNEngine', 'CloudFrontCDNEngine', 'cdn_engine_identity_map']


cdn_engine_identity_map = {
    e.__identity__.lower(): e for e in
    [CloudFrontCDNEngine]
}  # type: Dict[str, Type[BaseCDNEngine]]
