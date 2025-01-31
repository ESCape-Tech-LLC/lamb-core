import json
import logging
from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import VARCHAR, TypeDecorator

from lamb import exc
from lamb.json import JsonEncoder

logger = logging.getLogger(__name__)


class JSONType(TypeDecorator):
    """
    Universal SQLAlchemy JSON type.
    It uses native JSONB type for PostgreSQL engine and fallbacks to VARCHAR for other engines
    """

    impl = VARCHAR
    python_type = Any

    def __init__(self, *args, encoder_class=JsonEncoder, **kwargs):
        self._encoder_class = encoder_class
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        # Check that value is JSON serializable
        try:
            string_value = json.dumps(value, cls=self._encoder_class)
        except TypeError as e:
            raise exc.ServerError("Invalid data type to store as JSON") from e

        result = value if dialect.name == "postgresql" else string_value
        return result

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        result = value if dialect.name == "postgresql" else json.loads(value)
        return result

    def process_literal_param(self, value, dialect):
        return str(value)
