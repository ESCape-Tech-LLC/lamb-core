"""
Tests for lamb.utils.validators module.
"""

import uuid

import pytest
from sqlalchemy_utils import PhoneNumber

from lamb import exc
from lamb.utils import validators


class TestValidateRange:
    """Tests for validate_range function"""

    def test_valid_range_values(self):
        """Test valid values within range"""
        assert validators.validate_range(5, min_value=1, max_value=10) == 5
        assert validators.validate_range(1, min_value=1, max_value=10) == 1
        assert validators.validate_range(10, min_value=1, max_value=10) == 10

    def test_none_value_with_allow_none(self):
        """Test None value with allow_none=True"""
        assert validators.validate_range(None, min_value=1, max_value=10, allow_none=True) is None

    def test_value_below_minimum_raises_error(self):
        """Test value below minimum raises InvalidParamValueError"""
        with pytest.raises(exc.InvalidParamValueError):
            validators.validate_range(0, min_value=1, max_value=10)

    def test_value_above_maximum_raises_error(self):
        """Test value above maximum raises InvalidParamValueError"""
        with pytest.raises(exc.InvalidParamValueError):
            validators.validate_range(11, min_value=1, max_value=10)

    def test_invalid_type_raises_error(self):
        """Test invalid type raises InvalidParamTypeError"""
        with pytest.raises(exc.InvalidParamTypeError):
            validators.validate_range("invalid", min_value=1, max_value=10)


class TestValidateLength:
    """Tests for validate_length function"""

    def test_valid_length_values(self):
        """Test valid length values"""
        assert validators.validate_length("test", min_length=1, max_length=10) == "test"
        assert validators.validate_length("test", min_length=4, max_length=4) == "test"

    def test_none_value_with_allow_none(self):
        """Test None value with allow_none=True"""
        assert validators.validate_length(None, min_length=1, max_length=10, allow_none=True) is None

    def test_value_below_min_length_raises_error(self):
        """Test value below minimum length raises InvalidParamValueError"""
        with pytest.raises(exc.InvalidParamValueError):
            validators.validate_length("t", min_length=2, max_length=10)

    def test_value_above_max_length_raises_error(self):
        """Test value above maximum length raises InvalidParamValueError"""
        with pytest.raises(exc.InvalidParamValueError):
            validators.validate_length("too_long_string", min_length=1, max_length=10)

    def test_invalid_type_raises_error(self):
        """Test invalid type raises InvalidParamTypeError"""
        with pytest.raises(exc.InvalidParamTypeError):
            validators.validate_length(123, min_length=1, max_length=10)

    def test_trimming_functionality(self):
        """Test string trimming functionality"""
        result = validators.validate_length("  test  ", min_length=1, max_length=10, trimming=True)
        # Should trim whitespace
        assert result == "test"

    def test_empty_string_becomes_none(self):
        """Test that empty strings become None when empty_as_none=True"""
        result = validators.validate_length(
            "   ", min_length=0, max_length=10, trimming=True, empty_as_none=True, allow_none=True
        )
        assert result is None


class TestValidatePhoneNumber:
    """Tests for validate_phone_number function"""

    def test_valid_phone_number_string(self):
        """Test valid phone number string"""
        result = validators.validate_phone_number("+12125551234")
        assert isinstance(result, PhoneNumber)

    def test_none_value_with_allow_none(self):
        """Test None value with allow_none=True"""
        assert validators.validate_phone_number(None, allow_none=True) is None

    def test_phone_number_object_passthrough(self):
        """Test that PhoneNumber objects are passed through"""
        phone = PhoneNumber("+1234567890")
        result = validators.validate_phone_number(phone)
        assert result == phone

    def test_invalid_phone_number_raises_error(self):
        """Test invalid phone number raises InvalidParamValueError"""
        with pytest.raises(exc.InvalidParamValueError):
            validators.validate_phone_number("invalid_phone")


class TestValidateEmail:
    """Tests for validate_email function"""

    def test_valid_email(self):
        """Test valid email addresses"""
        valid_emails = ["test@example.com", "user.name@domain.co.uk", "user+tag@example.org"]

        for email in valid_emails:
            assert validators.validate_email(email) == email

    def test_none_value_with_allow_none(self):
        """Test None value with allow_none=True"""
        assert validators.validate_email(None, allow_none=True) is None

    def test_invalid_email_raises_error(self):
        """Test invalid email addresses raise InvalidParamValueError"""
        invalid_emails = ["invalid", "@example.com", "test@", "test@.com"]

        for email in invalid_emails:
            with pytest.raises(exc.InvalidParamValueError):
                validators.validate_email(email)


class TestValidateURL:
    """Tests for validate_url function"""

    def test_valid_urls(self):
        """Test valid URLs"""
        valid_urls = ["https://example.com", "http://example.com", "https://www.example.com/path?query=1"]

        for url in valid_urls:
            assert validators.validate_url(url) == url

    def test_none_value_with_allow_none(self):
        """Test None value with allow_none=True"""
        assert validators.validate_url(None, allow_none=True) is None

    def test_invalid_url_raises_error(self):
        """Test invalid URLs raise InvalidParamValueError"""
        invalid_urls = [
            "invalid",
            "http://",
            "ftp://example.com",  # ftp not in default schemes
        ]

        for url in invalid_urls:
            with pytest.raises(exc.InvalidParamValueError):
                validators.validate_url(url)


class TestValidatePort:
    """Tests for validate_port function"""

    def test_valid_port_numbers(self):
        """Test valid port numbers"""
        assert validators.validate_port(80) == 80
        assert validators.validate_port(443) == 443
        assert validators.validate_port(8080) == 8080
        assert validators.validate_port("8080") == 8080  # String conversion

    def test_none_value_with_allow_none(self):
        """Test None value with allow_none=True"""
        assert validators.validate_port(None, allow_none=True) is None

    def test_port_below_range_raises_error(self):
        """Test port below valid range raises error"""
        with pytest.raises((exc.InvalidParamValueError, exc.InvalidParamTypeError)):
            validators.validate_port(0)

    def test_port_above_range_raises_error(self):
        """Test port above valid range raises error"""
        with pytest.raises((exc.InvalidParamValueError, exc.InvalidParamTypeError)):
            validators.validate_port(65536)


class TestValidateIPAddress:
    """Tests for validate_ip_address function"""

    def test_valid_ipv4_addresses(self):
        """Test valid IPv4 addresses"""
        valid_ips = ["192.168.1.1", "127.0.0.1", "255.255.255.255"]
        for ip in valid_ips:
            assert validators.validate_ip_address(ip) == ip

    def test_valid_ipv6_addresses(self):
        """Test valid IPv6 addresses"""
        valid_ips = ["::1", "2001:db8::1"]
        for ip in valid_ips:
            assert validators.validate_ip_address(ip) == ip

    def test_none_value_with_allow_none(self):
        """Test None value with allow_none=True"""
        assert validators.validate_ip_address(None, allow_none=True) is None

    def test_invalid_ip_raises_error(self):
        """Test invalid IP addresses raise InvalidParamValueError"""
        invalid_ips = ["invalid", "999.999.999.999", ""]
        for ip in invalid_ips:
            with pytest.raises(exc.InvalidParamValueError):
                validators.validate_ip_address(ip)

    def test_version_checking(self):
        """Test IP version checking"""
        assert validators.validate_ip_address("192.168.1.1", version=4) == "192.168.1.1"

        assert validators.validate_ip_address("::1", version=6) == "::1"

        with pytest.raises(exc.InvalidParamValueError):
            validators.validate_ip_address("192.168.1.1", version=6)


class TestValidateNotEmpty:
    """Tests for validate_not_empty function"""

    def test_non_empty_string(self):
        """Test non-empty string"""
        assert validators.validate_not_empty("test") == "test"

    def test_empty_string_raises_error(self):
        """Test empty string raises InvalidParamValueError"""
        with pytest.raises(exc.InvalidParamValueError):
            validators.validate_not_empty("")

    def test_none_raises_error(self):
        """Test None raises InvalidParamTypeError"""
        with pytest.raises(exc.InvalidParamTypeError):
            validators.validate_not_empty(None)


class TestVOptUUID:
    """Tests for v_opt_uuid function"""

    def test_valid_uuid_string(self):
        """Test valid UUID string"""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = validators.v_opt_uuid(uuid_str)
        assert isinstance(result, uuid.UUID)

    def test_uuid_object_passthrough(self):
        """Test UUID object passthrough"""
        test_uuid = uuid.uuid4()
        result = validators.v_opt_uuid(test_uuid)
        assert result == test_uuid

    def test_none_returns_none(self):
        """Test None returns None"""
        assert validators.v_opt_uuid(None) is None

    def test_empty_string_returns_none(self):
        """Test empty string returns None"""
        assert validators.v_opt_uuid("") is None

    def test_whitespace_string_returns_none(self):
        """Test whitespace string returns None"""
        assert validators.v_opt_uuid("   ") is None

    def test_invalid_type_raises_error(self):
        """Test invalid type raises InvalidParamTypeError"""
        with pytest.raises(exc.InvalidParamTypeError):
            validators.v_opt_uuid(123)


class TestVOptString:
    """Tests for v_opt_string function"""

    def test_valid_string(self):
        """Test valid string"""
        assert validators.v_opt_string("test") == "test"

    def test_none_returns_none(self):
        """Test None returns None"""
        assert validators.v_opt_string(None) is None

    def test_non_string_type_raises_error(self):
        """Test non-string type raises InvalidParamTypeError"""
        with pytest.raises(exc.InvalidParamTypeError):
            validators.v_opt_string(123)

    def test_trimming_functionality(self):
        """Test trimming functionality"""
        result = validators.v_opt_string("  test  ")
        assert result == "test"

    def test_empty_after_trim_returns_none(self):
        """Test string that becomes empty after trimming returns None"""
        result = validators.v_opt_string("   ")
        assert result is None
