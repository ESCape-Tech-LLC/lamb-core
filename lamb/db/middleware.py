__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger(__name__)

from lamb.db.session import lamb_db_session_maker

__all__ = [
    'SQLAlchemyMiddleware'
]

class SQLAlchemyMiddleware(object):

    def process_request(self, request):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        """
        logger.debug('Processing request: %s %s' % (request.method, request.path))
        request.lamb_db_session = lamb_db_session_maker()

    def process_response(self, request, response):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        :param response: Response object
        :type response: django.http.HttpResponse
        """
        # logger.debug('Processing response: %s' % response)
        try:
            request.lamb_db_session.close()
        except AttributeError:
            pass
        finally:
            return response

    def process_exception(self, request, exception):
        """
        :param request: Request object
        :type request: pynm.utils.LambRequest
        :param exception: Exception object
        :type exception: Exception
        """
        logger.debug('Processing exception: %s.' % exception.message)
        try:
            request.lamb_db_session.rollback()
            request.lamb_db_session.close()
        except AttributeError:
            pass
