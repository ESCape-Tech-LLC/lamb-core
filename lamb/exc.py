from __future__ import annotations

import logging
from enum import IntEnum, unique
from typing import Any, List, Type, Union, Optional

__all__ = [
    "LambExceptionCodes",
    "ApiError",
    "ServerError",
    "NotRealizedMethodError",
    "ExternalServiceError",
    "ImproperlyConfiguredError",
    "DatabaseError",
    "ClientError",
    "NotAllowedMethodError",
    "NotExistError",
    "AlreadyExistError",
    "InvalidBodyStructureError",
    "InvalidParamValueError",
    "InvalidParamTypeError",
    "ThrottlingError",
    "UpdateRequiredError",
    "HumanFriendlyError",
    "HumanFriendlyMultipleError",
    "UserBlockedError",
    "RequestBodyTooBigError",
    "AuthTokenNotProvidedError",
    "AuthTokenInvalidError",
    "AuthTokenExpiredError",
    "AuthForbiddenError",
    "AuthCredentialsInvalidError",
    "RequestRangeError",
]


logger = logging.getLogger(__name__)


@unique
class LambExceptionCodes(IntEnum):
    # system
    Unknown = 0
    NotAllowed = 1
    NotRealized = 2
    InvalidStructure = 3
    InvalidParamValue = 4
    InvalidParamType = 5
    AuthTokenNotProvided = 6
    AuthTokenInvalid = 7
    AuthTokenExpired = 8
    AuthForbidden = 9
    NotExist = 10
    ExternalService = 11
    Database = 12
    AlreadyExist = 13
    RequestBodyTooBig = 14
    AuthCredentialsInvalid = 15
    RequestRange = 16

    # throttling and rate limiters
    Throttling = 101

    # application level
    UpdateRequired = 201
    HumanFriendly = 202
    HumanFriendlyMultiple = 203
    UserBlocked = 211  # new in 3.0.0


class ApiError(Exception):
    """Abstract rest api error"""

    # class level variables
    _app_error_code = LambExceptionCodes.Unknown
    _status_code = 500
    _message = None

    # attributes declaration
    message: str
    status_code: int
    app_error_code: int
    error_details: Optional[Any]

    def __init__(self, message=None, status_code=None, app_error_code=None, error_details=None):
        status_code = status_code or self._status_code
        app_error_code = app_error_code or self._app_error_code
        message = message or self._message

        self.status_code = status_code or self.__class__._status_code
        self.app_error_code = app_error_code or self.__class__._app_error_code
        self.message = message or self.__class__._message
        self.error_details = error_details

        super().__init__(self.message)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.app_error_code, self.status_code, self.message, self.error_details}>"


class ServerError(ApiError):
    """Common server side error"""

    _app_error_code = LambExceptionCodes.Unknown
    _status_code = 500
    _message = "Unknown server side error"


class ClientError(ApiError):
    """Common client side error"""

    _app_error_code = LambExceptionCodes.Unknown
    _status_code = 400
    _message = "Unknown client side error"


# server errors
class NotRealizedMethodError(ServerError):
    """Server side error for not realized functional"""

    _app_error_code = LambExceptionCodes.NotRealized
    _status_code = 501
    _message = "Required method or service declared but not realized or temporary disabled on server"


class ExternalServiceError(ServerError):
    """Server side error for problems with external services"""

    _app_error_code = LambExceptionCodes.ExternalService
    _status_code = 502
    _message = "Failed to communicate with external system"


class ImproperlyConfiguredError(ServerError):
    """Syntax sugar for improperly configured server params"""

    _app_error_code = LambExceptionCodes.Unknown
    _status_code = 500
    _message = "Improperly configured server side call"


class DatabaseError(ServerError):
    """Database error wrapper"""

    _app_error_code = LambExceptionCodes.Database
    _status_code = 500
    _message = "Database error occurred"


# client errors
class NotAllowedMethodError(ClientError):
    """Client side error for requesting not allowed HTTP method"""

    _app_error_code = LambExceptionCodes.NotAllowed
    _status_code = 405
    _message = "HTTP method not allowed on this endpoint"


class InvalidBodyStructureError(ClientError):
    """Client side invalid format of body error"""

    _app_error_code = LambExceptionCodes.InvalidStructure
    _status_code = 400
    _message = "Invalid body structure"


class InvalidParamValueError(ClientError):
    """Client side invalid params of request error"""

    _app_error_code = LambExceptionCodes.InvalidParamValue
    _status_code = 400
    _message = "Invalid param value"


class InvalidParamTypeError(ClientError):
    """Client side invalid param type error"""

    _app_error_code = LambExceptionCodes.InvalidParamType
    _status_code = 400
    _message = "Invalid param type"


class NotExistError(ClientError):
    """Client side error for not exist instance request"""

    _app_error_code = LambExceptionCodes.NotExist
    _status_code = 404
    _message = "Object not exist"


class AlreadyExistError(ClientError):
    """Client side error for already exist instance request"""

    _app_error_code = LambExceptionCodes.AlreadyExist
    _status_code = 400
    _message = "Object already exist"


class AuthTokenNotProvidedError(ClientError):
    """Client side error for invalid credentials structure"""

    _app_error_code = LambExceptionCodes.AuthTokenNotProvided
    _status_code = 401
    _message = "User auth token is not provided. You must be logged for this request."


class AuthTokenInvalidError(ClientError):
    """Client side error for invalid credentials value"""

    _app_error_code = LambExceptionCodes.AuthTokenInvalid
    _status_code = 401
    _message = "User auth token is not valid. You must be logged for this request."


class AuthTokenExpiredError(ClientError):
    """Client side error for expired credentials value"""

    _app_error_code = LambExceptionCodes.AuthTokenExpired
    _status_code = 401
    _message = "Provided user auth token has expired. Please renew it."


class AuthForbiddenError(ClientError):
    """Client side error for requesting authorized but forbidden resource"""

    _app_error_code = LambExceptionCodes.AuthForbidden
    _status_code = 403
    _message = "You have not access to this resource"


class AuthCredentialsInvalidError(ClientError):
    _app_error_code = LambExceptionCodes.AuthCredentialsInvalid
    _status_code = 401
    _message = "Invalid auth credentials"


class ThrottlingError(ClientError):
    """Client side error for requesting resources guarded with rate-limiters"""

    _app_error_code = LambExceptionCodes.Throttling
    _status_code = 429
    _message = "Too many requests"

    limits: Optional[list]

    def __init__(self, *args, limits=None, **kwargs):
        super(ThrottlingError, self).__init__(*args, **kwargs)
        self.limits = limits or []


class UserBlockedError(ClientError):
    """Client side error for ser profile blocked kind of errors"""

    _app_error_code = LambExceptionCodes.UserBlocked
    _status_code = 403
    _message = "User profile is blocked"


class UpdateRequiredError(ClientError):
    """Client side error for control requests device info fields in manner of version and platform pairs check"""

    _app_error_code = LambExceptionCodes.UpdateRequired
    _status_code = 400
    _message = "Client version deprecated, update required"


class HumanFriendlyError(ClientError):
    """Error for logic human friendly errors"""

    _app_error_code = LambExceptionCodes.HumanFriendly
    _status_code = 400
    _message = None


class HumanFriendlyMultipleError(HumanFriendlyError):
    """Error for multiple human friendly errors"""

    _app_error_code = LambExceptionCodes.HumanFriendlyMultiple
    _message = None
    _status_code = 400
    wrapped_errors: List[ApiError]

    def __init__(
        self,
        *args,
        wrapped_errors: List[Union[ApiError, Type[ApiError]]] = None,
        header: str = None,
        **kwargs,
    ):
        self.wrapped_errors = []
        if wrapped_errors:
            for e in wrapped_errors:
                if isinstance(e, ApiError):
                    _e = e
                elif issubclass(e, ApiError):
                    _e = e()
                else:
                    logger.warning(f"invalid exception type for wrapping: {e.__class__} -> {e}")
                    raise ServerError("Incorrect use of human multiple error block") from self
                self.wrapped_errors.append(_e)

        if len(args) == 0 and "message" not in kwargs:
            components = [e.message or "" for e in self.wrapped_errors]
            if header:
                components.insert(0, header)
            msg = ". ".join(components)
            kwargs.update({"message": msg})
            logger.warning(f"overridden: {msg}")

        super().__init__(*args, **kwargs)

        self.error_details = {
            "wrapped_messages": [str(e) if e.message is not None else None for e in self.wrapped_errors],
            "wrapped_details": [e.error_details for e in self.wrapped_errors],
        }


class RequestBodyTooBigError(ClientError):
    _app_error_code = LambExceptionCodes.RequestBodyTooBig
    _status_code = 400
    _message = "Request data too big"


class RequestRangeError(ClientError):
    _app_error_code = LambExceptionCodes.RequestRange
    _status_code = 416
    _message = "Requested Range Not Satisfiable"
