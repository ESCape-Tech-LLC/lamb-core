# -*- coding: utf-8 -*-
# __author__ = 'KoNEW'
import warnings
from lamb.utils import DeprecationClassHelper

from lamb.middleware.rest import LambRestApiJsonMiddleware
from lamb.middleware.cors import LambCorsMiddleware
from lamb.middleware.xray import LambXRayMiddleware

LambTracingMiddleware = DeprecationClassHelper(LambXRayMiddleware)

warnings.warn('module deprecated - use lamb.middleware instead', DeprecationWarning)


__all__ = ['LambRestApiJsonMiddleware', 'LambCorsMiddleware', 'LambXRayMiddleware', 'LambTracingMiddleware']
