from __future__ import annotations

import enum
import logging
from typing import Any, Type, TypeVar, Optional

# SQLAlchemy
import sqlalchemy as sa
from sqlalchemy_utils.types.scalar_coercible import ScalarCoercible

# Lamb Framework
from lamb import exc

__all__ = ["IntEnumType"]

logger = logging.getLogger(__name__)


ET = TypeVar("ET", enum.Enum, enum.IntEnum)


# database storage support
class IntEnumType(sa.types.TypeDecorator, ScalarCoercible):
    # meta
    impl = sa.Integer
    python_type = ET

    # internal attributes
    _enum_type: Type[ET]
    _impl_type: Type[sa.types.Integer]

    def __init__(self, enum_type: Type[ET], impl_type: Optional[Type[sa.Integer]] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._enum_type = enum_type
        self._impl_type = impl_type

    def load_dialect_impl(self, dialect):
        if self._impl_type is not None:
            return dialect.type_descriptor(self._impl_type)
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value: Optional[ET], dialect):
        if value is None:
            return None

        if isinstance(value, enum.Enum):
            return value.value
        else:
            return value

    def process_result_value(self, value: Optional[Any], dialect):
        if value is None:
            return None
        try:
            return self._enum_type(value)
        except ValueError as e:
            raise exc.InvalidParamValueError(f"Unknown enum value: {value}") from e

    def _coerce(self, value: Optional[Any]) -> Optional[ET]:
        if value is not None and not isinstance(value, enum.Enum):
            try:
                return self._enum_type(value)
            except ValueError as e:
                raise exc.InvalidParamValueError(f"Unknown enum value: {value}") from e
        return value
