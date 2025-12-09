"""
Django default error views

"""

from django.http import HttpRequest

from lamb.exc import ClientError, NotExistError, ServerError
from lamb.json.response import JsonResponse
from lamb.middleware.rest import LambRestApiJsonMiddleware

__all__ = ["page_not_found", "server_error", "bad_request"]


def page_not_found(request: HttpRequest, *_, **__) -> JsonResponse:
    """
    JSON 404 view
    """
    return LambRestApiJsonMiddleware.produce_error_response(request, NotExistError(), ignore_resolver=True)


def server_error(request: HttpRequest, *_, **__) -> JsonResponse:
    """
    JSON 500 view
    """
    return LambRestApiJsonMiddleware.produce_error_response(request, ServerError(), ignore_resolver=True)


def bad_request(request: HttpRequest, *_, **__) -> JsonResponse:
    """
    JSON 400 view
    """
    return LambRestApiJsonMiddleware.produce_error_response(request, ClientError("Bad request"), ignore_resolver=True)
