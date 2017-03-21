__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

LAMB_REST_APP_ERROR_UNKNOWN = 0
LAMB_REST_APP_ERROR_NOT_ALLOWED = 1
LAMB_REST_APP_ERROR_NOT_REALIZED = 2
LAMB_REST_APP_ERROR_PARAM_INVALID_STRUCTURE = 3
LAMB_REST_APP_ERROR_PARAM_INVALID_VALUE = 4
LAMB_REST_APP_ERROR_PARAM_INVALID_TYPE = 5
LAMB_REST_APP_ERROR_AUTH_NOT_PROVIDED = 6
LAMB_REST_APP_ERROR_AUTH_INVALID = 7
LAMB_REST_APP_ERROR_AUTH_EXPIRED = 8
LAMB_REST_APP_ERROR_AUTH_FORBIDDEN = 9
LAMB_REST_APP_ERROR_NOT_EXIST = 10
LAMB_REST_APP_ERROR_EXTERNAL_SERVICE = 11
LAMB_REST_APP_ERROR_DATABASE = 12

class ApiError(Exception):
    """ Abstract rest api error """
    def __init__(self, message=None, status_code=500, app_error_code=0, details=None):
        self.message = message
        self.status_code = status_code
        self.app_error_code = app_error_code
        self.details = details


class ServerError(ApiError):
    """ Common server side error """
    def __init__(self, *args, **kwargs):
        super(ServerError, self).__init__(*args, **kwargs)
        self.status_code = 500
        self.app_error_code = LAMB_REST_APP_ERROR_UNKNOWN


class ClientError(ApiError):
    """ Common client side error """
    def __init__(self, *args, **kwargs):
        super(ClientError, self).__init__(*args, **kwargs)
        self.status_code = 400
        self.app_error_code = LAMB_REST_APP_ERROR_UNKNOWN


class NotRealizedMethodError(ServerError):
    """ Server side error for not realized functional """
    def __init__(self, *args, **kwargs):
        super(NotRealizedMethodError, self).__init__(*args, **kwargs)
        self.status_code = 501
        self.app_error_code = LAMB_REST_APP_ERROR_NOT_REALIZED


class ExternalServiceError(ServerError):
    """ Server side error for problems with external services """
    def __init__(self, *args, **kwargs):
        super(ExternalServiceError, self).__init__(*args, **kwargs)
        self.status_code = 500
        self.app_error_code = LAMB_REST_APP_ERROR_EXTERNAL_SERVICE


class NotAllowedMethodError(ClientError):
    """ Client side error for requesting not allowed HTTP method """
    def __init__(self, *args, **kwargs):
        super(NotAllowedMethodError, self).__init__(*args, **kwargs)
        self.status_code = 405
        self.app_error_code = LAMB_REST_APP_ERROR_NOT_ALLOWED


class InvalidBodyStructureError(ClientError):
    """ Client side invalid format of body error """
    def __init__(self, *args, **kwargs):
        super(ClientError, self).__init__(*args, **kwargs)
        self.status_code = 400
        self.app_error_code = LAMB_REST_APP_ERROR_PARAM_INVALID_STRUCTURE


class InvalidParamValueError(ClientError):
    """ Client side invalid params of request error """
    def __init__(self, *args, **kwargs):
        super(ClientError, self).__init__(*args, **kwargs)
        self.status_code = 400
        self.app_error_code = LAMB_REST_APP_ERROR_PARAM_INVALID_VALUE


class InvalidParamTypeError(ClientError):
    """ Client side invalid param type error """
    def __init__(self, *args, **kwargs):
        super(ClientError, self).__init__(*args, **kwargs)
        self.status_code = 400
        self.app_error_code = LAMB_REST_APP_ERROR_PARAM_INVALID_TYPE


class NotExistError(ClientError):
    """ Client side error for not exist instance request """
    def __init__(self, *args, **kwargs):
        super(NotExistError, self).__init__(*args, **kwargs)
        self.status_code = 404
        self.app_error_code = LAMB_REST_APP_ERROR_NOT_EXIST


class AuthCredentialsIsNotProvided(ClientError):
    """ Client side error for invalid credentials structure """
    def __init__(self, *args, **kwargs):
        super(AuthCredentialsIsNotProvided, self).__init__(*args, **kwargs)
        self.status_code = 401
        self.app_error_code = LAMB_REST_APP_ERROR_AUTH_NOT_PROVIDED


class AuthCredentialsInvalid(ClientError):
    """ Client side error for invalid credentials value """
    def __init__(self, *args, **kwargs):
        super(AuthCredentialsInvalid, self).__init__(*args, **kwargs)
        self.status_code = 401
        self.app_error_code = LAMB_REST_APP_ERROR_AUTH_INVALID


class AuthCredentialsExpired(ClientError):
    """ Client side error for expired credentials value """
    def __init__(self, *args, **kwargs):
        super(AuthCredentialsExpired, self).__init__(*args, **kwargs)
        self.status_code = 401
        self.app_error_code = LAMB_REST_APP_ERROR_AUTH_EXPIRED


class AuthForbidden(ClientError):
    """ Client side error for requesting authorized but forbidden resource """
    def __init__(self, *args,**kwargs):
        super(AuthForbidden, self).__init__(*args, **kwargs)
        self.status_code = 403
        self.app_error_code = LAMB_REST_APP_ERROR_AUTH_FORBIDDEN
