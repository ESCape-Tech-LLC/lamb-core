# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging
import sqlalchemy as sa

from .session import lamb_db_session_maker
from sqlalchemy.orm.session import Session  as SASession


logger = logging.getLogger(__name__)


__all__ = ['lamb_db_context']


class lamb_db_context:

    _pooled: bool

    def __init__(self, pooled: bool = False):
        super().__init__()
        self._pooled = pooled

    def __enter__(self) -> SASession:
        logger.debug('Enter lamb database context')
        self.db_session = lamb_db_session_maker(pooled=self._pooled)
        return self.db_session

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug('Exit lamb database context')
        self.db_session.close()
