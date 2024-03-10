import logging

from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

# Lamb Framework
from lamb.utils import LambRequest
from lamb.db.session import lamb_db_session_maker

logger = logging.getLogger(__name__)


__all__ = ["LambSQLAlchemyMiddleware"]


class LambSQLAlchemyMiddleware(MiddlewareMixin):
    def process_request(self, request: LambRequest):
        """Appends lamb_db_session object to request instance"""
        logger.debug(f"<{self.__class__.__name__}>: Attaching DB session_maker")
        request.lamb_db_session = lamb_db_session_maker()

    def process_response(self, request: LambRequest, response: HttpResponse) -> HttpResponse:
        """Closes database connection session attached to request"""
        logger.debug(f"<{self.__class__.__name__}>: Closing DB session")
        try:
            request.lamb_db_session.close()
        except AttributeError:
            pass
        finally:
            return response

    def process_exception(self, request: LambRequest, exception: Exception):
        """Rollback and closes database connection session attached from request"""
        logger.debug(f"<{self.__class__.__name__}>: Rolling back DB session cause cause of error: {exception}")
        try:
            request.lamb_db_session.rollback()
            request.lamb_db_session.close()
        except AttributeError:
            pass
