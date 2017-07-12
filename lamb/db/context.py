# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

from .session import lamb_db_session_maker

__all__ = [
    'lamb_db_context'
]

class lamb_db_context:
    def __enter__(self):
        self.db_session = lamb_db_session_maker()
        return self.db_session
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db_session.close()