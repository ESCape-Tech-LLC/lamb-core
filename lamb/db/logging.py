# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import time
from django.conf import settings
from sqlalchemy.engine import Engine
from sqlalchemy import event

__all__ = [
    'sql_logging_enable', 'sql_logging_disable'
]


# TODO: fix - not work with 1.4-2.0 versions


def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

    if settings.LAMB_VERBOSE_SQL_LOG and settings.LAMB_VERBOSE_SQL_LOG_THRESHOLD is None:
        if executemany:
            print(f'Start query: [mode=executemany] -> {statement}, {parameters[0]} [total={len(parameters)}]')
            # print(f'Start query: [mode=executemany] -> {statement % parameters[0]} [total={len(parameters)}]')
        else:
            print(f'Start query: [mode=single] -> {statement}, {parameters}')
            # print(f'Start query: [mode=single] -> {statement % parameters}')


def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if settings.LAMB_VERBOSE_SQL_LOG:
        total = time.time() - conn.info['query_start_time'].pop(-1)
        _threshold = settings.LAMB_VERBOSE_SQL_LOG_THRESHOLD
        if _threshold is None:
            print(f'Total time: {total} sec.')
        elif total > _threshold:
            if executemany:
                print(f'[mode=executemany] -> {statement}, {parameters[0]}\n{total} sec.')
                # print(f'[mode=executemany] -> {statement % parameters[0]}\n{total} sec.')
            else:
                print(f'[mode=single] -> {statement}, {parameters}\n{total} sec.')
                # print(f'[mode=single] -> {statement % parameters}\n{total} sec.')



def sql_logging_disable():
    if event.contains(Engine, 'before_cursor_execute', _before_cursor_execute):
        event.remove(Engine, 'before_cursor_execute', _before_cursor_execute)
    if event.contains(Engine, 'after_cursor_execute', _after_cursor_execute):
        event.remove(Engine, 'after_cursor_execute', _after_cursor_execute)


def sql_logging_enable():
    if not event.contains(Engine, 'before_cursor_execute', _before_cursor_execute):
        event.listen(Engine, 'before_cursor_execute', _before_cursor_execute)
    if not event.contains(Engine, 'after_cursor_execute', _after_cursor_execute):
        event.listen(Engine, 'after_cursor_execute', _after_cursor_execute)
