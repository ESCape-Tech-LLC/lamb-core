# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import warnings

from lamb.utils import DeprecationClassHelper
from lamb.middleware.device_info import LambDeviceInfoMiddleware

__all__ = ['DeviceInfoMiddleware']


warnings.warn('module deprecated - use lamb.middleware instead', DeprecationWarning)


DeviceInfoMiddleware = DeprecationClassHelper(LambDeviceInfoMiddleware)
