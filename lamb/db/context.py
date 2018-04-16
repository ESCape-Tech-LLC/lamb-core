# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
from .session import lamb_db_session_maker


logger = logging.getLogger(__name__)


__all__ = [
    'lamb_db_context'
]


class lamb_db_context:

    def __enter__(self):
        logger.debug('Enter lamb database context')
        self.db_session = lamb_db_session_maker()
        return self.db_session

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug('Exit lamb database context')
        self.db_session.close()