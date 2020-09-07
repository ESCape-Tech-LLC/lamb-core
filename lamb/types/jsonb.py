# -*- coding: utf-8 -*-

import logging
import json
import six
from sqlalchemy import TypeDecorator, UnicodeText
from sqlalchemy.types import UserDefinedType
from sqlalchemy.dialects.postgresql.base import ischema_names

logger = logging.getLogger(__name__)


__all__ = ['SUAJSONBType']

try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    class PostgresJSONType(UserDefinedType):
        """
        Text search vector type for postgresql.
        """

        def get_col_spec(self):
            return 'json'

    ischema_names['json'] = PostgresJSONType
    JSONB = None


class SUAJSONBType(TypeDecorator):

    impl = UnicodeText

    def __init__(self, native=True, silent_error=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.native = native
        self.silent_error = silent_error

    @property
    def python_type(self):
        return dict

    def process_literal_param(self, value, dialect):
        return super(SUAJSONBType, self).process_literal_param(value, dialect)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql' and self.native:
            # Use the native JSONB type.
            if JSONB:
                return dialect.type_descriptor(JSONB())
            else:
                return dialect.type_descriptor(PostgresJSONType())
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        if dialect.name == 'postgresql' and JSONB and self.native:
            return value
        if value is not None:
            value = six.text_type(json.dumps(value))
        return value

    def process_result_value(self, value, dialect):
        if dialect.name == 'postgresql' and self.native:
            return value
        if value is not None:
            try:
                value = json.loads(value)
            except json.JSONDecodeError as e:
                if self.silent_error:
                    value = None
                else:
                    raise e
        return value
