# Lamb Framework
from lamb import exc
from lamb.utils import LambRequest
from lamb.rest.rest_view import RestView
from lamb.rest.decorators import rest_allowed_http_methods


@rest_allowed_http_methods(["GET", "POST"])
class InvalidParam(RestView):
    def get(self, request: LambRequest):
        raise exc.InvalidParamTypeError("")

    def post(self, request: LambRequest):
        raise exc.InvalidParamTypeError("")


def unknown(*_, **__):
    raise Exception("Unknown")
