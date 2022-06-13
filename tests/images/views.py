# Lamb Framework
from lamb.json import JsonResponse
from lamb.utils import LambRequest
from lamb.rest.rest_view import RestView
from lamb.rest.decorators import rest_allowed_http_methods
from lamb.service.image.utils import upload_images

from .model import SimpleImage


@rest_allowed_http_methods(["GET", "POST"])
class SimpleImageListView(RestView):
    def get(self, request: LambRequest):
        result = request.lamb_db_session.query(SimpleImage).all()
        return result

    def post(self, request: LambRequest):
        result = upload_images(request, SimpleImage.__slicing__, SimpleImage, "images_test")
        request.lamb_db_session.add_all(result)
        request.lamb_db_session.commit()
        return JsonResponse(result, status=201)
