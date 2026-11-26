
import pytest

from lamb.exc import (
    InvalidBodyStructureError,
    InvalidParamTypeError,
    ProgrammingError,
    ServerError,
)
from lamb.utils.dpath import dpath_value


class TestDpathValueKeyPathFormats:
    """Test different key_path formats"""
    
    def test_string_key_path_simple(self):
        """Test simple string key path"""
        data = {"key": "value"}
        result = dpath_value(data, "key")
        assert result == "value"
    
    def test_nested_key_path_with_list_format(self):
        """Test nested key path using list format as nested string notation not supported by default engine"""
        data = {"a": {"b": "value"}}
        result = dpath_value(data, ["a", "b"])
        assert result == "value"
    
    def test_list_key_path_simple(self):
        """Test simple list key path"""
        data = {"key": "value"}
        result = dpath_value(data, ["key"])
        assert result == "value"
    
    def test_list_key_path_nested(self):
        """Test nested list key path"""
        data = {"a": {"b": "value"}}
        result = dpath_value(data, ["a", "b"])
        assert result == "value"
    
    def test_tuple_key_path_simple(self):
        """Test simple tuple key path"""
        data = {"key": "value"}
        result = dpath_value(data, ("key",))
        assert result == "value"
    
    def test_tuple_key_path_nested(self):
        """Test nested tuple key path"""
        data = {"a": {"b": "value"}}
        result = dpath_value(data, ("a", "b"))
        assert result == "value"
    
    def test_key_path_format_equivalence(self):
        """Test that list and tuple key paths produce equivalent results"""
        data = {"a": {"b": {"c": "value"}}}
        
        result_list = dpath_value(data, ["a", "b", "c"])
        result_tuple = dpath_value(data, ("a", "b", "c"))
        
        assert result_list == result_tuple
        assert result_list == "value"
    
    def test_key_path_with_special_characters(self):
        """Test key paths with special characters using list format"""
        data = {"key.with.dots": {"sub-key": "value"}}
        result = dpath_value(data, ["key.with.dots", "sub-key"])
        assert result == "value"
    
    def test_key_path_with_numeric_keys(self):
        """Test key paths with numeric keys"""
        data = {"0": {"1": "value"}}
        result_list = dpath_value(data, ["0", "1"])
        
        assert result_list == "value"
    
    def test_key_path_with_unicode_keys(self):
        """Test key paths with unicode keys"""
        data = {"ключ": {"значение": "результат"}}
        result = dpath_value(data, ["ключ", "значение"])
        assert result == "результат"


class TestDpathValueTypeConversion:
    """Test type conversion functionality"""
    
    def test_valid_int_conversion(self):
        """Test valid string to int conversion"""
        data = {"key": "123"}
        result = dpath_value(data, "key", int)
        assert result == 123
        assert isinstance(result, int)
    
    def test_valid_float_conversion(self):
        """Test valid string to float conversion"""
        data = {"key": "123.45"}
        result = dpath_value(data, "key", float)
        assert result == 123.45
        assert isinstance(result, float)
    
    def test_valid_bool_conversion_true(self):
        """Test valid string to bool conversion (true values)"""
        data = {"key": "true"}
        result = dpath_value(data, "key", bool)
        assert result is True
    
    def test_valid_bool_conversion_false(self):
        """Test valid string to bool conversion (false values)"""
        # Note: In Python, bool("false") is True because any non-empty string is truthy
        # The dpath_value function uses Python's built-in bool() conversion
        data = {"key": ""}
        result = dpath_value(data, "key", bool)
        assert result is False
    
    def test_invalid_int_conversion_raises_error(self):
        """Test that invalid int conversion raises InvalidParamTypeError"""
        data = {"key": "1.234"}
        with pytest.raises(InvalidParamTypeError):
            dpath_value(data, "key", int)
    
    def test_another_invalid_int_conversion_raises_error(self):
        """Test another invalid int conversion case"""
        data = {"key": "1.0"}
        with pytest.raises(InvalidParamTypeError):
            dpath_value(data, "key", int)
    
    def test_non_numeric_string_to_int_raises_error(self):
        """Test that non-numeric string to int raises InvalidParamTypeError"""
        data = {"key": "abc"}
        with pytest.raises(InvalidParamTypeError):
            dpath_value(data, "key", int)
    
    def test_none_value_without_allow_none_raises_error(self):
        """Test that None value without allow_none raises InvalidParamTypeError"""
        data = {"key": None}
        with pytest.raises(InvalidParamTypeError):
            dpath_value(data, "key", str, allow_none=False)
    
    def test_none_value_with_allow_none_returns_none(self):
        """Test that None value with allow_none returns None"""
        data = {"key": None}
        result = dpath_value(data, "key", str, allow_none=True)
        assert result is None
    
    def test_same_type_no_conversion(self):
        """Test that same type value is not converted"""
        data = {"key": 123}
        result = dpath_value(data, "key", int)
        assert result == 123
        assert isinstance(result, int)





class TestDpathValueImplDict:
    """Test dict implementation with different engines"""
    
    @pytest.mark.parametrize("engine_fixture", ["dpath_dict_engine_reduce", "dpath_dict_engine_dpath"])
    def test_dict_simple_key(self, engine_fixture, request):
        """Test simple dict key access with different engines"""
        # Activate the requested engine fixture
        request.getfixturevalue(engine_fixture)
        
        data = {"key": "value"}
        result = dpath_value(data, "key")
        assert result == "value"
    
    @pytest.mark.parametrize("engine_fixture", ["dpath_dict_engine_reduce", "dpath_dict_engine_dpath"])
    def test_dict_nested_key(self, engine_fixture, request):
        """Test nested dict key access with different engines"""
        # Activate the requested engine fixture
        request.getfixturevalue(engine_fixture)
        
        data = {"a": {"b": "value"}}
        result = dpath_value(data, ["a", "b"])
        assert result == "value"


class TestDpathValueImplQueryDict:
    """Test QueryDict implementation"""
    
    def test_query_dict_string_key(self):
        """Test QueryDict with string key path"""
        from django.http.request import QueryDict
        
        query_dict = QueryDict("key=value")
        result = dpath_value(query_dict, "key")
        assert result == "value"
    
    def test_query_dict_single_item_list_key(self):
        """Test QueryDict with single-item list key path"""
        from django.http.request import QueryDict
        
        query_dict = QueryDict("key=value")
        result = dpath_value(query_dict, ["key"])
        assert result == "value"
    
    def test_query_dict_with_multi_element_list_raises_error(self):
        """Test that QueryDict with multi-element list key path raises InvalidBodyStructureError"""
        from django.http.request import QueryDict
        
        query_dict = QueryDict("key=value")
        with pytest.raises(InvalidBodyStructureError):
            dpath_value(query_dict, ["key", "subkey"])  # Multi-element list not supported


class TestDpathValueImplEnviron:
    """Test environment variables implementation"""
    
    def test_environment_variable_string_key(self):
        """Test environment variables with string key path"""
        import os
        os.environ["TEST_VAR"] = "test_value"
        
        result = dpath_value(os.environ, "TEST_VAR")
        assert result == "test_value"
    
    def test_environment_variable_single_item_list_key(self):
        """Test environment variables with single-item list key path - EXPECTED TO FAIL"""
        import os
        os.environ["TEST_VAR2"] = "test_value2"
        
        # This should raise a ProgrammingError because environment variable keys must be strings
        with pytest.raises(ProgrammingError):
            dpath_value(os.environ, ["TEST_VAR2"])
    
    def test_environment_with_multi_element_list_raises_error(self):
        """Test that environment with multi-element list key path raises ServerError"""
        import os
        with pytest.raises(ServerError):
            dpath_value(os.environ, ["key", "subkey"])  # Multi-element list not supported


class TestDpathValueImplEtree:
    """Test XML Element implementation"""
    
    def test_xml_element_string_key(self):
        """Test XML Element with string key path - Should work with proper XML handling"""
        from lxml import etree
        
        root = etree.fromstring("<root><child>text</child></root>")
        # The _impl_etree function should handle string key paths for XML elements
        # If this fails, it indicates an issue with XML element handling
        result = dpath_value(root, "child")
        assert result == "text"
    
    def test_xml_element_with_type_hint(self):
        """Test XML Element with type hint - Should work with proper XML handling"""
        from lxml import etree
        
        root = etree.fromstring('<root><child typeHint="int">123</child></root>')
        # The _impl_etree function should handle type hints for XML elements
        # If this fails, it indicates an issue with XML element handling
        result = dpath_value(root, "child", int)
        assert result == 123
    
    def test_xml_element_with_list_key_path_raises_error(self):
        """Test that XML Element with list key path raises InvalidParamTypeError"""
        from lxml import etree
        
        root = etree.fromstring("<root><child>text</child></root>")
        with pytest.raises(InvalidParamTypeError):
            dpath_value(root, ["child"])  # List key path not supported for XML


class TestDpathValueImplSettings:
    """Test Django Settings implementation"""
    
    def test_django_settings_string_key(self):
        """Test Django Settings with string key path"""
        from django.conf import settings
        
        # Mock a settings object with a test attribute
        original_value = getattr(settings, 'DEBUG', None)
        settings.DEBUG = True
        
        try:
            result = dpath_value(settings, "DEBUG")
            assert result is True
        finally:
            # Restore original value
            if original_value is not None:
                settings.DEBUG = original_value
            elif hasattr(settings, 'DEBUG'):
                delattr(settings, 'DEBUG')


class TestDpathValueErrorHandling:
    """Test error handling functionality"""
    
    def test_invalid_key_path_type_raises_server_error(self):
        """Test that invalid key_path type raises ServerError"""
        data = {"key": "value"}
        with pytest.raises(ServerError):
            dpath_value(data, 123)  # Invalid key_path type
    
    def test_missing_key_without_default_raises_error(self):
        """Test that missing key without default raises InvalidBodyStructureError"""
        data = {"key": "value"}
        with pytest.raises(InvalidBodyStructureError):
            dpath_value(data, "missing_key")
    
    def test_missing_key_with_default_returns_default(self):
        """Test that missing key with default returns default value"""
        data = {"key": "value"}
        result = dpath_value(data, "missing_key", default="default_value")
        assert result == "default_value"
    
    def test_none_dict_object_with_default_returns_default(self):
        """Test that None dict_object with default returns default"""
        result = dpath_value(None, "key", default="default_value")
        assert result == "default_value"
    
    def test_query_dict_with_multi_element_list_raises_error(self):
        """Test that QueryDict with multi-element list key path raises InvalidBodyStructureError"""
        from django.http.request import QueryDict
        
        query_dict = QueryDict("key=value")
        with pytest.raises(InvalidBodyStructureError):
            dpath_value(query_dict, ["key", "subkey"])  # Multi-element list not supported
    
    def test_environment_with_multi_element_list_raises_error(self):
        """Test that environment with multi-element list key path raises ServerError"""
        import os
        with pytest.raises(ServerError):
            dpath_value(os.environ, ["key", "subkey"])  # Multi-element list not supported
    
    def test_xml_element_with_list_key_path_raises_error(self):
        """Test that XML Element with list key path raises InvalidParamTypeError"""
        from lxml import etree
        
        root = etree.fromstring("<root><child>text</child></root>")
        with pytest.raises(InvalidParamTypeError):
            dpath_value(root, ["child"])  # List key path not supported for XML


class TestDpathValueEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_string_key(self):
        """Test handling of empty string key - should raise error with dpath engine"""
        data = {"": "value"}
        # Empty string keys are not allowed by default in dpath
        with pytest.raises(ServerError):
            dpath_value(data, "")
    
    def test_empty_list_key_path(self):
        """Test handling of empty list key path - should raise error"""
        data = {"key": "value"}
        # Empty list key path is not valid
        with pytest.raises(InvalidBodyStructureError):
            dpath_value(data, [])
    
    def test_deeply_nested_structure(self):
        """Test deeply nested structure using list format"""
        data = {"a": {"b": {"c": {"d": {"e": {"f": "deep_value"}}}}}}
        result = dpath_value(data, ["a", "b", "c", "d", "e", "f"])
        assert result == "deep_value"
    
    def test_list_index_access(self):
        """Test accessing list elements by index"""
        data = {"list": [1, 2, {"nested": "value"}, 4]}
        result = dpath_value(data, ["list", 2, "nested"])
        assert result == "value"
    
    def test_complex_mixed_structure(self):
        """Test complex mixed structure with multiple data types"""
        data = {
            "users": [
                {"name": "Alice", "age": "30", "active": "true"},
                {"name": "Bob", "age": "25", "active": "false"}
            ],
            "metadata": {
                "total": "2",
                "page": "1"
            }
        }
        
        # Test list access
        alice_name = dpath_value(data, ["users", 0, "name"])
        assert alice_name == "Alice"
        
        # Test list access with type conversion
        alice_age = dpath_value(data, ["users", 0, "age"], int)
        assert alice_age == 30
        
        # Test boolean conversion
        alice_active = dpath_value(data, ["users", 0, "active"], bool)
        assert alice_active is True
        
        # Test metadata access
        total = dpath_value(data, ["metadata", "total"], int)
        assert total == 2