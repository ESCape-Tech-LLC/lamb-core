# -*- coding: utf-8 -*-

__all__ = ['BaseCDNEngine']


class BaseCDNEngine:
    __identity__ = None
    required_param_list = []

    def get_image_cdn_url(self, uploader, *args, **kwargs) -> str:
        raise NotImplementedError(f'CDN engine {self.__class__.__name__}: get_image_cdn_url method is not implemented')
