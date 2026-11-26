"""
Transformer and validator tests for dpath utilities.
"""
import enum
import uuid
from datetime import date
from functools import partial

import pytest

from lamb import exc
from lamb.utils import dpath_value, transformers


class TestDpathValueTransformers:
    """Tests for transformer functionality"""
    
    def test_date_transformer(self):
        """Test date transformation with partial function"""
        data = {"date": "2017-04-20"}
        result = dpath_value(
            data, 
            "date", 
            transform=partial(transformers.transform_date, __format="%Y-%m-%d")
        )
        assert result == date(2017, 4, 20)
    
    def test_boolean_transformer_various_formats(self):
        """Test boolean transformation with various formats"""
        test_cases = [
            ({"flag": "1"}, "flag", True),
            ({"flag": "0"}, "flag", False),
            ({"flag": "true"}, "flag", True),
            ({"flag": "false"}, "flag", False),
            ({"flag": "TRUE"}, "flag", True),
            ({"flag": "FALSE"}, "flag", False),
        ]
        
        for data, key, expected in test_cases:
            result = dpath_value(data, key, transform=transformers.transform_boolean)
            assert result == expected
    
    def test_enum_transformer(self):
        """Test enum transformation"""
        
        class StringEnum(enum.StrEnum):
            FIRST = "first"
            SECOND = "second"
            THIRD = "third"
        
        data = {
            "enum_first": "first",
            "enum_second": "second",
            "enum_third": "third"
        }
        
        # Test each enum value
        result_first = dpath_value(
            data, 
            "enum_first", 
            transform=partial(transformers.transform_string_enum, enum_class=StringEnum)
        )
        assert result_first == StringEnum.FIRST
        
        result_second = dpath_value(
            data, 
            "enum_second", 
            transform=partial(transformers.transform_string_enum, enum_class=StringEnum)
        )
        assert result_second == StringEnum.SECOND
        
        result_third = dpath_value(
            data, 
            "enum_third", 
            transform=partial(transformers.transform_string_enum, enum_class=StringEnum)
        )
        assert result_third == StringEnum.THIRD
    
    def test_uuid_transformer(self):
        """Test UUID transformation"""
        test_uuid = "2752051C-1EEA-4B8C-A29C-A9C72B7DB727"
        data = {"uuid_field": test_uuid}
        
        result = dpath_value(data, "uuid_field", transform=transformers.transform_uuid)
        assert isinstance(result, uuid.UUID)
        assert str(result).upper() == test_uuid.upper()
    
    def test_transformer_with_default_value(self):
        """Test transformer with default value when key is missing"""
        data = {"existing_key": "value"}
        
        # Test with existing key
        result_existing = dpath_value(
            data,
            "existing_key",
            transform=transformers.transform_boolean,
            default=False
        )
        # Since "value" is not a valid boolean string, it will use default
        assert result_existing == False
        
        # Test with missing key
        result_missing = dpath_value(
            data,
            "missing_key",
            transform=transformers.transform_boolean,
            default=True
        )
        assert result_missing == True
    
    def test_transformer_with_none_value_and_allow_none(self):
        """Test transformer with None value and allow_none=True"""
        data = {"none_field": None}
        
        # When allow_none=True, transformer should not be applied to None values
        result = dpath_value(
            data,
            "none_field",
            transform=transformers.transform_boolean,
            allow_none=True
        )
        assert result is None
    
    def test_chained_transformers_partial_application(self):
        """Test chained transformers using partial functions"""
        def multiply_transform(value, multiplier=1):
            try:
                return int(value) * multiplier
            except (ValueError, TypeError):
                return 0
        
        data = {"number": "5"}
        
        # Create a partially applied transformer
        double_transformer = partial(multiply_transform, multiplier=2)
        
        result = dpath_value(
            data,
            "number",
            transform=double_transformer
        )
        assert result == 10  # 5 * 2


class TestDpathValueValidators:
    """Tests for validator functionality"""
    
    def test_custom_validation_function(self):
        """Test custom validation function"""
        def validate_positive_number(value):
            num = int(value)
            if num <= 0:
                raise ValueError("Number must be positive")
            return num
        
        data = {"positive_number": "10"}
        
        result = dpath_value(
            data,
            "positive_number",
            transform=validate_positive_number
        )
        assert result == 10
    
    def test_validation_failure_raises_error(self):
        """Test that validation failures raise appropriate errors"""
        def validate_positive_number(value):
            num = int(value)
            if num <= 0:
                raise ValueError("Number must be positive")
            return num
        
        data = {"negative_number": "-5"}
        
        with pytest.raises(exc.ServerError):  # Gets wrapped by dpath_value
            dpath_value(
                data,
                "negative_number",
                transform=validate_positive_number
            )
    
    def test_validation_with_type_conversion(self):
        """Test validation combined with type conversion"""
        def validate_range(value):
            if not 1 <= value <= 100:
                raise ValueError("Value must be between 1 and 100")
            return value
        
        data = {"score": "75"}
        
        result = dpath_value(
            data,
            "score",
            int,  # First convert to int
            transform=validate_range  # Then validate
        )
        assert result == 75
    
    def test_email_validator(self):
        """Test email validation"""
        import re
        
        def validate_email(email):
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, email):
                raise ValueError("Invalid email format")
            return email
        
        data = {"email": "test@example.com"}
        
        result = dpath_value(
            data,
            "email",
            transform=validate_email
        )
        assert result == "test@example.com"
        
        # Test invalid email
        invalid_data = {"email": "invalid-email"}
        with pytest.raises(exc.ServerError):
            dpath_value(
                invalid_data,
                "email",
                transform=validate_email
            )


class TestDpathValueComplexTransformations:
    """Tests for complex transformation scenarios"""
    
    def test_nested_transformation_with_fallback(self):
        """Test nested transformation with fallback values"""
        def safe_int_transform(value):
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        
        # Test data with various value types
        data = {
            "valid_int": "123",
            "invalid_int": "abc",
            "none_value": None,
            "empty_string": ""
        }
        
        # Test valid integer
        result_valid = dpath_value(
            data,
            "valid_int",
            transform=safe_int_transform
        )
        assert result_valid == 123
        
        # Test invalid integer (falls back to 0 via transformer)
        result_invalid = dpath_value(
            data,
            "invalid_int",
            transform=safe_int_transform
        )
        assert result_invalid == 0
        
        # Test empty string (falls back to 0 via transformer)
        result_empty = dpath_value(
            data,
            "empty_string",
            transform=safe_int_transform
        )
        assert result_empty == 0
    
    def test_transformation_with_additional_parameters(self):
        """Test transformation functions that use additional parameters"""
        def format_string_transform(value, prefix="", suffix=""):
            return f"{prefix}{value}{suffix}"
        
        data = {"name": "John"}
        
        result = dpath_value(
            data,
            "name",
            transform=lambda x: format_string_transform(x, prefix="Mr. ", suffix=" Jr.")
        )
        assert result == "Mr. John Jr."
    
    def test_list_transformation(self):
        """Test transformation of list values"""
        def join_list_transform(value):
            if isinstance(value, list):
                return ", ".join(str(item) for item in value)
            return str(value)
        
        data = {"items": ["apple", "banana", "cherry"]}
        
        result = dpath_value(
            data,
            "items",
            transform=join_list_transform
        )
        assert result == "apple, banana, cherry"
    
    def test_conditional_transformation(self):
        """Test conditional transformations based on value content"""
        def conditional_transform(value):
            if isinstance(value, str):
                if value.lower() in ['true', '1', 'yes']:
                    return True
                elif value.lower() in ['false', '0', 'no']:
                    return False
            return bool(value)
        
        test_cases = [
            ({"flag": "true"}, "flag", True),
            ({"flag": "false"}, "flag", False),
            ({"flag": "1"}, "flag", True),
            ({"flag": "0"}, "flag", False),
            ({"flag": "yes"}, "flag", True),
            ({"flag": "no"}, "flag", False),
        ]
        
        for data, key, expected in test_cases:
            result = dpath_value(data, key, transform=conditional_transform)
            assert result == expected


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])