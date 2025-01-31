from __future__ import annotations

import logging

from lamb.execution_time.meter import ExecutionTimeMeter
from lamb.utils import LambRequest, get_current_request

logger = logging.getLogger(__name__)


__all__ = ["get_global_etm"]


def get_global_etm(request: LambRequest | None = None) -> ExecutionTimeMeter:
    request = request or get_current_request()
    return request.lamb_execution_meter if request is not None else ExecutionTimeMeter()
