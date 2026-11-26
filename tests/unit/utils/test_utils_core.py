"""
Tests for lamb.utils.core module.
"""

import urllib.parse

import furl
import pytest

from lamb.utils import core


class TestCompact:
    """Tests for compact function"""

    def test_compact_list_removes_none(self):
        """Test that None values are removed from lists"""
        test_list = [1, None, 2, None, 3]
        result = core.compact(test_list)
        assert result == [1, 2, 3]

    def test_compact_dict_removes_none(self):
        """Test that None values are removed from dictionaries"""
        test_dict = {"a": 1, "b": None, "c": 2}
        result = core.compact(test_dict)
        assert result == {"a": 1, "c": 2}

    def test_compact_tuple_removes_none(self):
        """Test that None values are removed from tuples"""
        test_tuple = (1, None, 2, None, 3)
        result = core.compact(test_tuple)
        assert result == (1, 2, 3)

    def test_compact_preserves_false_values(self):
        """Test that False values are preserved"""
        test_list = [1, False, 2, None, 3]
        result = core.compact(test_list)
        assert result == [1, False, 2, 3]

    def test_compact_preserves_zero_values(self):
        """Test that zero values are preserved"""
        test_list = [1, 0, 2, None, 3]
        result = core.compact(test_list)
        assert result == [1, 0, 2, 3]

    def test_compact_with_traverse(self):
        """Test compact with traverse=True"""
        test_list = [[1, None, 2], None, [3, None, 4]]
        result = core.compact(test_list, traverse=True)
        assert result == [[1, 2], [3, 4]]

    def test_compact_with_collapse(self):
        """Test compact with collapse=True"""
        test_list = [[1, 2], [], [3, 4], []]
        result = core.compact(test_list, traverse=True, collapse=True)
        assert result == [[1, 2], [3, 4]]


class TestImportByName:
    """Tests for import_by_name function"""

    def test_import_module(self):
        """Test importing a module"""
        result = core.import_by_name("os")
        import os

        assert result == os

    def test_import_function(self):
        """Test importing a function"""
        result = core.import_by_name("os.path.join")
        from os.path import join

        assert result == join

    def test_import_class(self):
        """Test importing a class"""
        result = core.import_by_name("collections.OrderedDict")
        from collections import OrderedDict

        assert result == OrderedDict

    def test_import_nonexistent_raises_error(self):
        """Test importing nonexistent module raises ImportError"""
        with pytest.raises(ImportError):
            core.import_by_name("nonexistent.module.function")


class TestRandomString:
    """Tests for random_string function"""

    def test_default_length(self):
        """Test default length of 10"""
        result = core.random_string()
        assert len(result) == 10
        assert isinstance(result, str)

    def test_custom_length(self):
        """Test custom length"""
        result = core.random_string(length=20)
        assert len(result) == 20

    def test_custom_charset(self):
        """Test custom character set"""
        result = core.random_string(length=10, char_set="a")
        assert result == "a" * 10


class TestListChunks:
    """Tests for list_chunks function"""

    def test_chunking_evenly_divisible(self):
        """Test chunking with evenly divisible list"""
        test_list = [1, 2, 3, 4, 5, 6]
        result = list(core.list_chunks(test_list, 2))
        assert result == [[1, 2], [3, 4], [5, 6]]

    def test_chunking_remainder(self):
        """Test chunking with remainder"""
        test_list = [1, 2, 3, 4, 5]
        result = list(core.list_chunks(test_list, 2))
        assert result == [[1, 2], [3, 4], [5]]

    def test_chunk_size_larger_than_list(self):
        """Test chunk size larger than list"""
        test_list = [1, 2, 3]
        result = list(core.list_chunks(test_list, 5))
        assert result == [[1, 2, 3]]

    def test_empty_list(self):
        """Test chunking empty list"""
        result = list(core.list_chunks([], 2))
        assert result == []


class TestGetRedisUrl:
    """Tests for get_redis_url function"""

    def test_default_parameters(self):
        """Test with default parameters"""
        result = core.get_redis_url()
        expected = "redis://localhost/0"
        assert result == expected

    def test_custom_host_port(self):
        """Test with custom host and port"""
        result = core.get_redis_url(host="example.com", port=1234)
        expected = "redis://example.com:1234/0"
        assert result == expected

    def test_with_password(self):
        """Test with password"""
        result = core.get_redis_url(password="secret")
        # Parse URL to check components
        parsed = urllib.parse.urlparse(result)
        assert parsed.scheme == "redis"
        assert parsed.hostname == "localhost"
        # Note: furl omits default ports, so port will be None
        assert parsed.port is None
        # Password is handled specially in netloc
        assert "secret@" in result or parsed.password == "secret"

    def test_with_username(self):
        """Test with username"""
        result = core.get_redis_url(username="user")
        # Parse URL to check components
        parsed = urllib.parse.urlparse(result)
        assert parsed.username == "user"

    def test_with_db(self):
        """Test with custom database"""
        result = core.get_redis_url(db=5)
        expected = "redis://localhost/5"
        assert result == expected


class TestMaskedDict:
    """Tests for masked_dict function"""

    def test_masking_keys(self):
        """Test masking specific keys"""
        test_dict = {"password": "secret", "token": "secret", "username": "user"}
        result = core.masked_dict(test_dict, "password", "token")
        assert result == {"password": "*****", "token": "*****", "username": "user"}

    def test_none_input(self):
        """Test None input returns None"""
        assert core.masked_dict(None) is None

    def test_no_matching_keys(self):
        """Test with no matching keys"""
        test_dict = {"username": "user", "email": "test@example.com"}
        result = core.masked_dict(test_dict, "password")
        assert result == test_dict


class TestMaskedUrl:
    """Tests for masked_url function"""

    def test_masking_password(self):
        """Test masking password in URL"""
        test_url = "redis://user:password@localhost:6379/0"
        result = core.masked_url(test_url)
        expected = "redis://user:*****@localhost/0"
        assert result == expected

    def test_furl_object(self):
        """Test with furl object"""
        test_url = furl.furl("redis://user:password@localhost:6379/0")
        result = core.masked_url(test_url)
        expected = "redis://user:*****@localhost/0"
        assert result == expected

    def test_none_input(self):
        """Test None input returns None"""
        assert core.masked_url(None) is None


class TestMaskedString:
    """Tests for masked_string function"""

    def test_masking_string(self):
        """Test masking string"""
        result = core.masked_string("secret")
        assert result == "*****"

    def test_none_input(self):
        """Test None input returns None"""
        assert core.masked_string(None) is None


class TestLazyDescriptors:
    """Tests for lazy descriptors"""

    class LazyTestObject:
        def __init__(self):
            self._call_count = 0

        @core.lazy
        def lazy_property(self):
            self._call_count += 1
            return self._call_count

    def test_lazy_evaluation(self):
        """Test that lazy property is evaluated only once"""
        obj = self.LazyTestObject()

        # First access - should compute
        assert obj.lazy_property == 1
        # Second access - should return cached value
        assert obj.lazy_property == 1
        # Call count should still be 1
        assert obj._call_count == 1

    def test_lazy_invalidate(self):
        """Test lazy property invalidation"""
        obj = self.LazyTestObject()

        # First access
        assert obj.lazy_property == 1
        # Invalidate
        core.lazy.invalidate(obj, "lazy_property")
        # Second access - should recompute
        assert obj.lazy_property == 2


class TestDeprecationHelpers:
    """Tests for deprecation helper classes"""

    def test_deprecation_class_mixin_warning(self, recwarn):
        """Test that DeprecationClassMixin issues warning"""

        class DeprecatedClass(core.DeprecationClassMixin):
            def __init__(self):
                super().__init__()

        # Create instance - should issue warning
        DeprecatedClass()

        # Check that warning was issued
        assert len(recwarn) > 0
        assert any(issubclass(w.category, DeprecationWarning) for w in recwarn)


class TestGetFullClsInstanceName:
    """Tests for get_full_cls_instance_name function"""

    def test_instance_name(self):
        """Test getting name for instance"""
        obj = TestGetFullClsInstanceName()
        result = core.get_full_cls_instance_name(obj)
        assert result == "test_utils_core.TestGetFullClsInstanceName"

    def test_class_name(self):
        """Test getting name for class"""
        result = core.get_full_cls_instance_name(TestGetFullClsInstanceName)
        assert result == "test_utils_core.TestGetFullClsInstanceName"
