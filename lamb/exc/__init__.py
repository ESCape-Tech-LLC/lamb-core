# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
from enum import IntEnum, unique

__all__ = [
    'LambExceptionCodes',
    'ApiError', 'ServerError', 'ClientError',
    'NotRealizedMethodError', 'NotAllowedMethodError', 'NotExistError', 'AlreadyExistError',
    'ExternalServiceError',
    'InvalidBodyStructureError', 'InvalidParamValueError', 'InvalidParamTypeError',
    'AuthCredentialsIsNotProvided', 'AuthCredentialsInvalid', 'AuthCredentialsExpired', 'AuthForbidden',
    'ImproperlyConfiguredError'
]


logger = logging.getLogger(__name__)


@unique
class LambExceptionCodes(IntEnum):
    Unknown = 0
    NotAllowed = 1
    NotRealized = 2
    InvalidStructure = 3
    InvalidParamValue = 4
    InvalidParamType = 5
    AuthNotProvided = 6
    AuthInvalid = 7
    AuthExpired = 8
    AuthForbidden = 9
    NotExist = 10
    ExternalService = 11
    Database = 12
    AlreadyExist = 13


class ApiError(Exception):
    """ Abstract rest api error """
    def __init__(self, message=None, status_code=500, app_error_code=0, error_details=None):
        self.message = message
        self.status_code = status_code
        self.app_error_code = app_error_code
        self.error_details = error_details


class ServerError(ApiError):
    """ Common server side error """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 500
        self.app_error_code = LambExceptionCodes.Unknown


class ClientError(ApiError):
    """ Common client side error """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 400
        self.app_error_code = LambExceptionCodes.Unknown


# server errors
class NotRealizedMethodError(ServerError):
    """ Server side error for not realized functional """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 501
        self.app_error_code = LambExceptionCodes.NotRealized


class ExternalServiceError(ServerError):
    """ Server side error for problems with external services """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 500
        self.app_error_code = LambExceptionCodes.ExternalService


class ImproperlyConfiguredError(ServerError):
    """ Syntax sugar for improperly configured server params """
    def __init__(self, *args, message='Improperly configured server side call', **kwargs):
        if len(args) == 0:
            kwargs.update({
                'message': message
            })
        super().__init__(*args, **kwargs)
        self.status_code = 500
        self.app_error_code = LambExceptionCodes.Unknown

# client errors
class NotAllowedMethodError(ClientError):
    """ Client side error for requesting not allowed HTTP method """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 405
        self.app_error_code = LambExceptionCodes.NotAllowed


class InvalidBodyStructureError(ClientError):
    """ Client side invalid format of body error """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 400
        self.app_error_code = LambExceptionCodes.InvalidStructure


class InvalidParamValueError(ClientError):
    """ Client side invalid params of request error """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 400
        self.app_error_code = LambExceptionCodes.InvalidParamValue


class InvalidParamTypeError(ClientError):
    """ Client side invalid param type error """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 400
        self.app_error_code = LambExceptionCodes.InvalidParamType


class NotExistError(ClientError):
    """ Client side error for not exist instance request """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 404
        self.app_error_code = LambExceptionCodes.NotExist


class AlreadyExistError(ClientError):
    """ Client side error for already exist instance request"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 400
        self.app_error_code = LambExceptionCodes.AlreadyExist


class AuthCredentialsIsNotProvided(ClientError):
    """ Client side error for invalid credentials structure """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 401
        self.app_error_code = LambExceptionCodes.AuthNotProvided


class AuthCredentialsInvalid(ClientError):
    """ Client side error for invalid credentials value """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 401
        self.app_error_code = LambExceptionCodes.AuthInvalid


class AuthCredentialsExpired(ClientError):
    """ Client side error for expired credentials value """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 401
        self.app_error_code = LambExceptionCodes.AuthExpired


class AuthForbidden(ClientError):
    """ Client side error for requesting authorized but forbidden resource """
    def __init__(self, *args,**kwargs):
        super().__init__(*args, **kwargs)
        self.status_code = 403
        self.app_error_code = LambExceptionCodes.AuthForbidden
