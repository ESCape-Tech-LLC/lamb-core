# -*- coding: utf-8 -*-
import enum

from lamb.exc import ClientError


@enum.unique
class InAppErrorCodes(enum.IntEnum):
    InAppAppleSandbox = 901


class InAppAppleSandboxError(ClientError):
    """ Error for a situation when received receipt is for a test environment """
    _app_error_code = InAppErrorCodes.InAppAppleSandbox
    _status_code = 403
    _message = 'Received receipt is for a test environment'
