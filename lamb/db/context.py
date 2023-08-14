import logging

# SQLAlchemy
from sqlalchemy.orm.session import Session as SASession

from .session import lamb_db_session_maker

logger = logging.getLogger(__name__)


__all__ = ["lamb_db_context"]


class lamb_db_context:
    _pooled: bool
    _db_key: str

    def __init__(self, pooled: bool = False, db_key: str = "default"):
        super().__init__()
        self._pooled = pooled
        self._db_key = db_key

    def __enter__(self) -> SASession:
        logger.debug("Enter lamb database context")
        self.db_session = lamb_db_session_maker(pooled=self._pooled, db_key=self._db_key, sync=True)
        return self.db_session

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Exit lamb database context")
        self.db_session.close()

    async def __aenter__(self):
        logger.debug("Enter lamb database context (async)")
        self.db_session = lamb_db_session_maker(pooled=self._pooled, db_key=self._db_key, sync=False)
        return self.db_session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Exit lamb database context (async)")
        await self.db_session.close()
