import enum
import logging
from typing import Any, TypeVar

import sqlalchemy as sa
from sqlalchemy_utils.types.scalar_coercible import ScalarCoercible

from lamb import exc
from lamb.contrib.handbook import HandbookEnumMixin

logger = logging.getLogger(__name__)

ET = TypeVar("ET")


class IntStrEnum(HandbookEnumMixin, enum.Enum):
    """
    Simple subclass of `HandbookMixin`
        - ensure that first arg is type(int) and second is type(str)
        - validates forced that first and second arguments unique within enum
    """

    # cache titles
    _ignore_ = ["_title_map"]
    _title_map: dict[str, Any] = {}

    def __init__(self, *args, **kwargs):
        # check datatypes
        if len(args) < 2:
            logger.error("Expected args length for IntStrEnum should be at least 2")
            raise exc.ProgrammingError
        if not isinstance(args[0], int):
            logger.error("IntStrEnum expects a int value as first argument")
            raise exc.ProgrammingError
        if not isinstance(args[1], str):
            logger.error("IntStrEnum expects str value as second argument")
            raise exc.ProgrammingError

        # check pair both elements unique
        code = int(args[0])
        title = str(args[1]).upper()
        exist_codes = [getattr(e, self.__attrs__[0]) for e in self.__class__.__members__.values()]
        exist_titles = [getattr(e, self.__attrs__[1]).upper() for e in self.__class__.__members__.values()]
        if code in exist_codes:
            raise exc.ProgrammingError(f"Not unique code value: {code}")
        if title in exist_titles:
            raise exc.ProgrammingError(f"Not unique title: {title}")

        # fill attributes with super
        super().__init__(*args, **kwargs)

    @classmethod
    def _missing_(cls, value: object):
        """Support for creation from string version and deprecated titles also"""
        # early return and normalize
        if isinstance(value, int) or not isinstance(value, str):
            # raise exc.InvalidParamValueError(f'{value} is not valid value for {cls.__name__}')
            raise ValueError(f"{value} is not valid value for {cls.__name__}")

        value = value.upper()

        # create cache on-demand
        if not hasattr(cls, "_title_map"):
            cls._title_map = {e.title.upper(): e for e in cls}

        result = cls._title_map.get(value, None)
        if result is None:
            # raise exc.InvalidParamValueError(f'{value} is not valid value for {cls.__name__}')
            raise ValueError(f"{value} is not a valid value for {cls.__name__}")
        else:
            return result


class IntStrEnumType(sa.types.TypeDecorator, ScalarCoercible):
    """Specific enum type - in database stored as int field, in serialize represents data in form of string"""

    # meta
    _enum_type: type[ET]  # underlying enum type
    _impl_type: type[sa.types.Integer]

    impl = sa.Integer

    @property
    def python_type(self):
        return self._enum_type

    def __init__(
        self,
        enum_type: type[ET],
        impl_type: type[sa.Integer] | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._enum_type = enum_type
        self._impl_type = impl_type

    def load_dialect_impl(self, dialect):
        if self._impl_type is not None:
            return dialect.type_descriptor(self._impl_type)
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value: ET | None, dialect):
        if value is None:
            return None

        if isinstance(value, IntStrEnum):
            return value.value
        else:
            return value

    def process_result_value(self, value: Any | None, dialect):
        if value is None:
            return None
        try:
            return self._enum_type(value)
        except ValueError as e:
            raise exc.InvalidParamValueError(f"Unknown enum value: {value}") from e

    def _coerce(self, value: Any | None) -> ET | None:
        if value is not None and not isinstance(value, self._enum_type):
            try:
                return self._enum_type(value)
            except ValueError as e:
                raise exc.InvalidParamValueError(f"Unknown enum value: {value}") from e
        return value
