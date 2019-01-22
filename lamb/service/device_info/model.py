# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

from dataclasses import dataclass
from lamb.types import LambLocale

__all__ = [
    'DeviceInfo'
]

@dataclass(frozen=True)
class DeviceInfo(object):
    """A device info class """
    device_family: str = None
    device_platform: str = None
    device_os: str = None
    app_version: str = None
    app_build: int = None
    device_locale: LambLocale = None
