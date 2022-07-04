import logging

# Lamb Framework
from lamb.utils import DeprecationClassHelper
from lamb.middleware.db import LambSQLAlchemyMiddleware

logger = logging.getLogger(__name__)


__all__ = ["SQLAlchemyMiddleware", "LambSQLAlchemyMiddleware"]


SQLAlchemyMiddleware = DeprecationClassHelper(LambSQLAlchemyMiddleware)
