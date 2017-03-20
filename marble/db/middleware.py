__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

import logging

from marble.db.session import marble_db_session_maker

logger = logging.getLogger('django')

class SQLAlchemyMiddleware(object):

    def process_request(self, request):
        """
        :param request: Request object
        :type request: pynm.utils.PYNMRequest
        """
        logger.debug('SQLAlchemyMiddleware. Processing request: %s %s' % (request.method, request.path))
        request.marble_db_session = marble_db_session_maker()

    def process_response(self, request, response):
        """
        :param request: Request object
        :type request: pynm.utils.PYNMRequest
        :param response: Response object
        :type response: django.http.HttpResponse
        """
        logger.debug('SQLAlchemyMiddleware. Processing response: %s' % response)
        try:
            request.marble_db_session.close()
        except AttributeError:
            pass
        finally:
            return response

    def process_exception(self, request, exception):
        """
        :param request: Request object
        :type request: pynm.utils.PYNMRequest
        :param exception: Exception object
        :type exception: Exception
        """
        logger.debug('SQLAlchemyMiddleware. Processing exception: %s.' % exception.message)
        try:
            request.marble_db_session.rollback()
            request.marble_db_session.close()
        except AttributeError:
            pass
