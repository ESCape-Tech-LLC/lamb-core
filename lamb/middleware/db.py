import contextlib
import logging

from django.conf import settings

from lamb.db.context import lamb_db_context
from lamb.db.session import lamb_db_session_maker
from lamb.middleware.base import LambMiddlewareMixin
from lamb.utils import LambRequest

logger = logging.getLogger(__name__)


__all__ = ["LambSQLAlchemyMiddleware"]


class LambSQLAlchemyMiddleware(LambMiddlewareMixin):
    def __call__(self, request: LambRequest):
        if self.async_mode:
            return self.__acall__(request)
        with contextlib.ExitStack() as stack:
            db_sessions = {}
            for db_key in settings.LAMB_DB_CONFIG:
                db_session = stack.enter_context(lamb_db_context(db_key=db_key, pooled=True))
                db_sessions[db_key] = db_session
                if db_key == "default":
                    request.lamb_db_session = db_session

            request.lamb_db_session_map = db_sessions
            logger.debug(f"<{self.__class__.__name__}>: Attaching DB session_maker - sync")
            return self.get_response(request)

    async def __acall__(self, request: LambRequest):
        async with contextlib.AsyncExitStack() as stack:
            db_sessions = {}
            for db_key in settings.LAMB_DB_CONFIG:
                db_session = await stack.enter_async_context(lamb_db_context(db_key=db_key, pooled=True))
                db_sessions[db_key] = db_session
                if db_key == "default":
                    request.lamb_db_session = db_session

            request.lamb_db_session_map = db_sessions
            logger.debug(f"<{self.__class__.__name__}>: Attaching DB session contexts - async")
            return await self.get_response(request)
