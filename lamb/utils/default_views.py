"""
Django default error views

"""

from django.http import HttpRequest

# Lamb Framework
from lamb.json.response import JsonResponse

__all__ = ["page_not_found", "server_error", "bad_request"]


def error_message(message: str = "") -> dict:
    """
    Returns standard error's payload

    :param message: Error message
    :return: Dict for response
    """
    return {"error_code": 0, "error_message": message, "error_details": None}  # Unknown  # Not needed


def page_not_found(request: HttpRequest, *_, **__) -> JsonResponse:
    """
    JSON 404 view
    """
    return JsonResponse(request=request, status=404, data=error_message("Not found"))


def server_error(request: HttpRequest, *_, **__) -> JsonResponse:
    """
    JSON 500 view
    """
    return JsonResponse(request=request, status=500, data=error_message("Server error"))


def bad_request(request: HttpRequest, *_, **__) -> JsonResponse:
    """
    JSON 400 view
    """
    return JsonResponse(request=request, status=400, data=error_message("Bad Request"))
