# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


from lamb.types import LambLocale

__all__ = [
    'DeviceInfo'
]


class DeviceInfo(object):
    """A device info class
    :type device_family: str
    :type device_platform: str
    :type device_os: str
    :type app_version: str
    :type app_build: int
    :type device_locale: LambLocale
    """
    def __init__(self, device_family=None, device_platform=None, device_os=None,
                 device_locale=None, app_version=None, app_build=None):
        self.device_family = device_family
        self.device_platform = device_platform
        self.device_os = device_os
        self.device_locale = device_locale
        self.app_version = app_version
        self.app_build = app_build

    def __str__(self):
        return 'DeviceInfo: %s (%s)/%s:%s. App=%s(%s)' \
               % (self.device_platform, self.device_os, self.device_family,
                  self.device_locale, self.app_version, self.app_build)