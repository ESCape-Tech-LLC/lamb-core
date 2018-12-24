from lamb import exc
from lamb.rest.decorators import rest_allowed_http_methods
from lamb.rest.rest_view import RestView
from lamb.utils import LambRequest


@rest_allowed_http_methods(['GET', 'POST'])
class InvalidParam(RestView):
    def get(self, request: LambRequest):
        raise exc.InvalidParamTypeError('')

    def post(self, request: LambRequest):
        raise exc.InvalidParamTypeError('')


def unknown(*_, **__):
    raise Exception('Unknown')
