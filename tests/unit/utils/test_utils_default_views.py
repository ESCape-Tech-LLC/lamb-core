"""
Tests for lamb.utils.default_views module.
"""

import json
from unittest.mock import Mock

from lamb.json.response import JsonResponse
from lamb.utils import default_views


class TestDefaultViews:
    """Tests for default view functions"""

    def test_page_not_found(self):
        """Test page_not_found view returns correct JSON response"""
        # Create a mock request
        request = Mock()
        request.path = "/nonexistent/"

        # Call the view
        response = default_views.page_not_found(request, Exception("Test"))

        # Check response type
        assert isinstance(response, JsonResponse)

        # Check status code
        assert response.status_code == 404

        # Check content
        content = response.content.decode("utf-8")
        assert "object not exist" in content.lower()
        assert "10" in content  # error_code for NotExistError

    def test_server_error(self):
        """Test server_error view returns correct JSON response"""
        # Create a mock request
        request = Mock()

        # Call the view
        response = default_views.server_error(request)

        # Check response type
        assert isinstance(response, JsonResponse)

        # Check status code
        assert response.status_code == 500

        # Check content
        content = response.content.decode("utf-8")
        assert "unknown server side error" in content.lower()
        assert "0" in content  # error_code for ServerError

    def test_bad_request(self):
        """Test bad_request view returns correct JSON response"""
        # Create a mock request
        request = Mock()
        request.path = "/bad-request/"

        # Call the view
        response = default_views.bad_request(request, Exception("Bad Request"))

        # Check response type
        assert isinstance(response, JsonResponse)

        # Check status code
        assert response.status_code == 400

        # Check content
        content = response.content.decode("utf-8")
        assert "bad request" in content.lower()
        assert "0" in content  # error_code for ClientError

    def test_response_format_consistency(self):
        """Test that all views return consistent JSON format"""
        request = Mock()
        request.path = "/test/"

        # Test 404 response
        response_404 = default_views.page_not_found(request, Exception("Not Found"))
        data_404 = json.loads(response_404.content.decode())

        # Test 500 response
        response_500 = default_views.server_error(request)
        data_500 = json.loads(response_500.content.decode())

        # Test 400 response
        response_400 = default_views.bad_request(request, Exception("Bad Request"))
        data_400 = json.loads(response_400.content.decode())

        # Check that all responses have similar structure
        for data in [data_404, data_500, data_400]:
            assert isinstance(data, dict)
            # Should have error-related keys
            assert "error_code" in data
            assert "error_message" in data
            assert "error_details" in data
