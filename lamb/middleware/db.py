import logging

from lamb.db.session import lamb_db_session_maker
from lamb.middleware.base import LambMiddlewareMixin
from lamb.utils import LambRequest

logger = logging.getLogger(__name__)


__all__ = ["LambSQLAlchemyMiddleware"]


class LambSQLAlchemyMiddleware(LambMiddlewareMixin):
    def __call__(self, request: LambRequest):
        if self.async_mode:
            return self.__acall__(request)
        with lamb_db_session_maker(sync=True, pooled=True) as db_session:
            logger.debug(f"<{self.__class__.__name__}>: Attaching DB session_maker - sync")
            request.lamb_db_session = db_session
            return self.get_response(request)

    async def __acall__(self, request: LambRequest):
        async with lamb_db_session_maker(sync=False, pooled=True) as db_session:
            logger.debug(f"<{self.__class__.__name__}>: Attaching DB session_maker - async")
            request.lamb_db_session = db_session
            return await self.get_response(request)


# class LambSQLAlchemyMiddleware(MiddlewareMixin):
#     def process_request(self, request: LambRequest):
#         """Appends lamb_db_session object to request instance"""
#         logger.debug(f"<{self.__class__.__name__}>: Attaching DB session_maker")
#         request.lamb_db_session = lamb_db_session_maker()
#
#     def process_response(self, request: LambRequest, response: HttpResponse) -> HttpResponse:
#         """Closes database connection session attached to request"""
#         logger.debug(f"<{self.__class__.__name__}>: Closing DB session")
#         try:
#             request.lamb_db_session.close()
#         except AttributeError:
#             pass
#         finally:
#             return response
#
#     def process_exception(self, request: LambRequest, exception: Exception):
#         """Rollback and closes database connection session attached from request"""
#         logger.debug(f"<{self.__class__.__name__}>: Rolling back DB session cause cause of error: {exception}")
#         try:
#             request.lamb_db_session.rollback()
#             request.lamb_db_session.close()
#         except AttributeError:
#             pass
