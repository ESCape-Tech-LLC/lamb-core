# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

from typing import Optional
from dataclasses import dataclass
from lamb.types import LambLocale

__all__ = [
    'DeviceInfo'
]


@dataclass(frozen=True)
class DeviceInfo(object):
    """A device info class """
    device_family: Optional[str] = None
    device_platform: Optional[str] = None
    device_os: Optional[str] = None
    app_version: Optional[str] = None
    app_build: Optional[int] = None
    device_locale: Optional[LambLocale] = None
