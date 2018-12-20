# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


import logging

from django.http import HttpResponse

from lamb.db.session import lamb_db_session_maker
from lamb.utils import LambRequest


logger = logging.getLogger(__name__)


__all__ = ['SQLAlchemyMiddleware']


class SQLAlchemyMiddleware(object):

    def process_request(self, request: LambRequest):
        """ Appends lamb_db_session object to request instance """
        logger.debug('Appending lamb database session to request: %s %s' % (request.method, request.path))
        request.lamb_db_session = lamb_db_session_maker()

    def process_response(self, request: LambRequest, response: HttpResponse) -> HttpResponse:
        """ Closes database connection session attached to request """
        logger.debug('Closing lamb database session from request: %s %s' % (request.method, request.path))
        try:
            request.lamb_db_session.close()
        except AttributeError:
            pass
        finally:
            return response

    def process_exception(self, request: LambRequest, exception: Exception):
        """ Rollback and closes database connection session attached from request """
        logger.debug(
            'Rolling back anc closing lamb database session from request: %s %s' % (request.method, request.path))
        try:
            request.lamb_db_session.rollback()
            request.lamb_db_session.close()
        except AttributeError:
            pass
