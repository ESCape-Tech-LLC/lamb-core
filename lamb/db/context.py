import logging

from sqlalchemy.orm.session import Session as SASession

from .session import lamb_db_session_maker

logger = logging.getLogger(__name__)


__all__ = ["lamb_db_context"]


class lamb_db_context:
    _pooled: bool
    _db_key: str

    def __init__(self, pooled: bool = False, db_key: str = "default"):
        self._pooled = pooled
        self._db_key = db_key

    def __enter__(self) -> SASession:
        logger.debug(
            f"<{self.__class__.__name__}>. enter lamb database context (sync): db_key={self._db_key}, pooled={self._pooled}"
        )
        self.db_session = lamb_db_session_maker(pooled=self._pooled, db_key=self._db_key, sync=True)
        return self.db_session

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug(
            f"<{self.__class__.__name__}>. exit lamb database context (sync): db_key={self._db_key}, sync={self._pooled}"
        )
        self.db_session.close()

    async def __aenter__(self):
        logger.debug(
            f"<{self.__class__.__name__}>. enter lamb database context (async): db_key={self._db_key}, pooled={self._pooled}"
        )
        self.db_session = lamb_db_session_maker(pooled=self._pooled, db_key=self._db_key, sync=False)
        return self.db_session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug(
            f"<{self.__class__.__name__}>. exit lamb database context (async): db_key={self._db_key}, sync={self._pooled}"
        )
        await self.db_session.close()
