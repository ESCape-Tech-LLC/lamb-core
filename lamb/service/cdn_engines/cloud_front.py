# -*- coding: utf-8 -*-

from django.conf import settings
from furl.furl import furl

from lamb.service.cdn_engines import BaseCDNEngine

__all__ = ['CloudFrontCDNEngine']


class CloudFrontCDNEngine(BaseCDNEngine):
    __identity__ = 'CloudFrontCDNEngine'
    required_param_list = ['cdn_base_url']

    def __init__(self, cdn_base_url=None, *args, **kwargs):
        cdn_base_url = cdn_base_url or settings.LAMB_CDN_ENGINE_PARAMS['CLOUDFRONT_CDN_BASE_URL']
        super(CloudFrontCDNEngine, self).__init__(*args, **kwargs)
        self.cdn_base_url = cdn_base_url

    def get_image_cdn_url(self, uploader, *args, **kwargs) -> str:
        if 'relative_path' not in kwargs:
            raise ValueError(f'Required relative_path variable at {self.__identity__}.get_image_cdn_url')
        relative_path = kwargs['relative_path']
        result_url = furl(self.cdn_base_url)
        result_url.path.add(relative_path)
        return result_url.url
