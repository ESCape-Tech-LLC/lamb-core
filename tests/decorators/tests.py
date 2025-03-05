import logging
from io import StringIO
from unittest import mock

# Lamb Framework
from lamb.exc import NotAllowedMethodError
from lamb.log.decorators import suppress_logging
from lamb.rest.rest_view import RestView
from lamb.rest.decorators import rest_allowed_http_methods

from tests.testcases import LambTestCase


@rest_allowed_http_methods(["GET"])
class View(RestView):
    """Let's preserve class docstring!"""

    def get(*args, **kwargs):
        """Let's preserve method docstring!"""
        return "OK"


class TastRestAllowedHttpMethods(LambTestCase):
    def test_method_called(self):
        request = mock.Mock()
        request.method = "GET"
        assert View(request) == "OK"

    def test_method_not_allowed(self):
        request = mock.Mock()
        request.method = "POST"
        with self.assertRaises(NotAllowedMethodError):
            assert View(request)

    def test_docstring_preserved(self):
        assert View.__doc__ == "Let's preserve class docstring!"
        assert View.get.__doc__ == "Let's preserve method docstring!"
