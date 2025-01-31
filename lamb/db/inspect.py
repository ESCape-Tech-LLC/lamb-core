import logging

# SQLAlchemy
import sqlalchemy as sa
from sqlalchemy.inspection import inspect

# Lamb Framework
from lamb.exc import ServerError
from lamb.utils.core import lazy

__all__ = ["ModelInspector"]


logger = logging.getLogger(__name__)


class ModelInspector(object):
    def __init__(self, model_class):
        self.model_class = model_class

    @lazy
    def inspect(self):
        """Inspection object for model class used in init process"""
        return inspect(self.model_class)

    @lazy
    def pkey(self) -> sa.Column:
        """Model class primary key column"""
        model_primary_key = self.inspect.primary_key
        if len(model_primary_key) == 0:
            raise ServerError("Model class %s doesn't have any primary key" % self.model_class.__name__)
        if len(model_primary_key) > 1:
            raise ServerError(
                "Model inspector auto model primary key field introspection "
                "doesn't support multiple columns primary key. Model class is %s" % self.model_class.__name__
            )
        return model_primary_key[0]

    @lazy
    def pkey_name(self) -> str:
        """Model class primary key field name"""
        return self.pkey.name

    @lazy
    def pkey_type(self) -> type:
        """Model class primary key field data type"""
        return self.pkey.type
