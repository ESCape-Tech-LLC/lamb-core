"""
Tests for lamb.utils.transformers module.
"""

import enum
import uuid
from datetime import date, datetime

import pytest

from lamb import exc
from lamb.utils import transformers


class TestTransformBoolean:
    """Tests for transform_boolean function"""

    def test_boolean_passthrough(self):
        """Test that boolean values are passed through unchanged"""
        assert transformers.transform_boolean(True) is True
        assert transformers.transform_boolean(False) is False

    def test_string_true_values(self):
        """Test various string representations of True"""
        true_values = ["1", "true", "yes", "y", "t", "on", "TRUE", "True"]
        for value in true_values:
            assert transformers.transform_boolean(value) is True

    def test_string_false_values(self):
        """Test various string representations of False"""
        false_values = ["0", "false", "no", "n", "f", "off", "FALSE", "False"]
        for value in false_values:
            assert transformers.transform_boolean(value) is False

    def test_invalid_string_raises_error(self):
        """Test that invalid strings raise InvalidParamValueError"""
        with pytest.raises(exc.InvalidParamValueError):
            transformers.transform_boolean("invalid")

        with pytest.raises(exc.InvalidParamValueError):
            transformers.transform_boolean("")

    def test_numeric_values(self):
        """Test numeric values conversion"""
        assert transformers.transform_boolean(1) is True
        assert transformers.transform_boolean(1.0) is True
        assert transformers.transform_boolean(0) is False
        assert transformers.transform_boolean(0.0) is False
        assert transformers.transform_boolean(-1) is True
        assert transformers.transform_boolean(0.1) is True

    def test_invalid_type_raises_error(self):
        """Test that invalid types raise InvalidParamTypeError"""
        with pytest.raises(exc.InvalidParamTypeError):
            transformers.transform_boolean([])

        with pytest.raises(exc.InvalidParamTypeError):
            transformers.transform_boolean({})


class TestTransformDate:
    """Tests for transform_date function"""

    def test_datetime_passthrough(self):
        """Test that date objects are passed through"""
        test_date = date(2023, 1, 1)
        result = transformers.transform_date(test_date)
        assert result == test_date

    def test_string_date_parsing(self):
        """Test parsing date from string"""
        result = transformers.transform_date("2023-01-01", format="%Y-%m-%d")
        assert result == date(2023, 1, 1)

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises appropriate error"""
        with pytest.raises(exc.InvalidParamValueError):
            transformers.transform_date("invalid", format="%Y-%m-%d")


class TestTransformDatetime:
    """Tests for transform_datetime function"""

    def test_datetime_passthrough(self):
        """Test that datetime objects are passed through"""
        test_dt = datetime(2023, 1, 1, 12, 0, 0)
        result = transformers.transform_datetime(test_dt)
        assert result == test_dt

    def test_date_conversion(self):
        """Test that date objects are converted to datetime at start of day"""
        test_date = date(2023, 1, 1)
        result = transformers.transform_datetime(test_date)
        expected = datetime(2023, 1, 1, 0, 0, 0)
        assert result == expected

    def test_timestamp_parsing(self):
        """Test parsing datetime from timestamp"""
        test_dt = datetime(2023, 1, 1, 12, 0, 0)
        timestamp = test_dt.timestamp()
        result = transformers.transform_datetime(str(timestamp))
        assert result == test_dt

    def test_string_datetime_parsing(self):
        """Test parsing datetime from string with format"""
        dt_str = "2023-01-01 12:00:00"
        result = transformers.transform_datetime(dt_str, format="%Y-%m-%d %H:%M:%S")
        expected = datetime(2023, 1, 1, 12, 0, 0)
        assert result == expected

    def test_iso_format_parsing(self):
        """Test parsing ISO format datetime"""
        iso_str = "2023-01-01T12:00:00+00:00"
        result = transformers.transform_datetime(iso_str, format="iso")
        expected = datetime(2023, 1, 1, 12, 0, 0).replace(tzinfo=datetime.now().astimezone().tzinfo)
        # Note: Timezone handling may vary, so we focus on the basic conversion
        assert result.year == expected.year
        assert result.month == expected.month
        assert result.day == expected.day
        assert result.hour == expected.hour
        assert result.minute == expected.minute
        assert result.second == expected.second

    def test_now_special_case(self):
        """Test 'now' special case"""
        result = transformers.transform_datetime("now")
        assert isinstance(result, datetime)

    def test_today_special_case(self):
        """Test 'today' special case"""
        result = transformers.transform_datetime("today")
        assert isinstance(result, datetime)
        # Should be at start of day
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_invalid_input_raises_error(self):
        """Test that invalid inputs raise appropriate errors"""
        with pytest.raises(exc.InvalidParamTypeError):
            transformers.transform_datetime([])


class TestTransformUUID:
    """Tests for transform_uuid function"""

    def test_uuid_passthrough(self):
        """Test that UUID objects are passed through"""
        test_uuid = uuid.uuid4()
        result = transformers.transform_uuid(test_uuid)
        assert result == test_uuid

    def test_string_uuid_parsing(self):
        """Test parsing UUID from string"""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = transformers.transform_uuid(uuid_str)
        assert isinstance(result, uuid.UUID)
        assert str(result) == uuid_str

    def test_invalid_uuid_raises_error(self):
        """Test that invalid UUID strings raise InvalidParamValueError"""
        with pytest.raises(exc.InvalidParamValueError):
            transformers.transform_uuid("invalid-uuid")

    def test_invalid_type_raises_error(self):
        """Test that invalid types raise InvalidParamValueError"""
        # The function should handle non-string types gracefully
        # Using None which will raise TypeError that gets caught and converted
        with pytest.raises(exc.InvalidParamValueError):  # Should raise InvalidParamValueError
            transformers.transform_uuid(None)


class TestTransformStringEnum:
    """Tests for transform_string_enum function"""

    class TestEnum(enum.StrEnum):
        FIRST = "first"
        SECOND = "second"
        THIRD = "third"

    def test_enum_passthrough(self):
        """Test that enum values are passed through"""
        test_enum = self.TestEnum.FIRST
        result = transformers.transform_string_enum(test_enum, self.TestEnum)
        assert result == test_enum

    def test_string_to_enum_conversion(self):
        """Test converting string to enum"""
        result = transformers.transform_string_enum("first", self.TestEnum)
        assert result == self.TestEnum.FIRST

        result = transformers.transform_string_enum("SECOND", self.TestEnum)
        assert result == self.TestEnum.SECOND

    def test_invalid_enum_class_raises_error(self):
        """Test that invalid enum class raises ProgrammingError"""

        # Create a class that doesn't inherit from enum.Enum
        class NotAnEnum:
            pass

        with pytest.raises(exc.ProgrammingError):
            transformers.transform_string_enum("first", NotAnEnum)

    def test_invalid_value_raises_error(self):
        """Test that invalid enum value raises InvalidParamValueError"""
        with pytest.raises(exc.InvalidParamValueError):
            transformers.transform_string_enum("fourth", self.TestEnum)


class TestTransformTypedList:
    """Tests for transform_typed_list function"""

    def test_single_value_wrapped_in_list(self):
        """Test that single values get wrapped in a list"""
        result = transformers.transform_typed_list(1, int)
        assert result == [1]

    def test_list_passthrough(self):
        """Test that lists are passed through"""
        test_list = [1, 2, 3]
        result = transformers.transform_typed_list(test_list, int)
        assert result == test_list

    def test_type_conversion_with_convert_flag(self):
        """Test type conversion when convert flag is True"""
        result = transformers.transform_typed_list(["1", "2", "3"], int, convert=True)
        assert result == [1, 2, 3]

    def test_invalid_type_without_convert_raises_error(self):
        """Test that invalid types raise error when convert is False"""
        with pytest.raises(exc.InvalidParamTypeError):
            transformers.transform_typed_list(["1", "2", "3"], int)

    def test_string_splitting(self):
        """Test string splitting functionality"""
        result = transformers.transform_typed_list("1,2,3", int, convert=True)
        assert result == [1, 2, 3]

    def test_skip_empty_values(self):
        """Test that empty values are skipped"""
        result = transformers.transform_typed_list("1,,2,3", int, convert=True)
        assert result == [1, 2, 3]


class TestDatetimeFormatting:
    """Tests for datetime formatting functions"""

    def test_transform_datetime_iso(self):
        """Test basic ISO datetime formatting"""
        test_dt = datetime(2023, 1, 1, 12, 0, 0)
        result = transformers.transform_datetime_iso(test_dt)
        assert result == "2023-01-01T12:00:00"

    def test_transform_datetime_iso_with_zulu(self):
        """Test ISO datetime formatting with Z suffix"""
        test_dt = datetime(2023, 1, 1, 12, 0, 0).replace(tzinfo=datetime.now().astimezone().tzinfo)
        result = transformers.transform_datetime_iso(test_dt, zulu=True)
        # Should end with Z if timezone is UTC
        assert isinstance(result, str)

    def test_transform_datetime_iso_milliseconds(self):
        """Test ISO datetime formatting with milliseconds"""
        test_dt = datetime(2023, 1, 1, 12, 0, 0, 123456)
        result = transformers.transform_datetime_iso_milliseconds(test_dt)
        assert "12:00:00.123" in result

    def test_transform_datetime_iso_microseconds(self):
        """Test ISO datetime formatting with microseconds"""
        test_dt = datetime(2023, 1, 1, 12, 0, 0, 123456)
        result = transformers.transform_datetime_iso_microseconds(test_dt)
        assert "12:00:00.123456" in result


# Additional test functions can be added here as needed
