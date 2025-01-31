import time

from django.conf import settings

# SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

__all__ = ["sql_logging_enable", "sql_logging_disable"]


# TODO: fix - not work with 1.4-2.0 versions


def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.time())

    if settings.LAMB_LOG_SQL_VERBOSE and settings.LAMB_LOG_SQL_VERBOSE_THRESHOLD is None:
        if executemany:
            # TODO: it depends on driver and sqlalchemy version - so should be adapted to properly calculate total
            print(f"Start query: [mode=executemany] {statement} [total=?]")
        else:
            print(f"Start query: [mode=single] -> {statement}, {parameters}")


def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if settings.LAMB_LOG_SQL_VERBOSE:
        total = time.time() - conn.info["query_start_time"].pop(-1)
        _threshold = settings.LAMB_LOG_SQL_VERBOSE_THRESHOLD
        if _threshold is None:
            print(f"Total time: {total} sec.")
        elif total > _threshold:
            if executemany:
                # TODO: it depends on driver and sqlalchemy version - so should be adapted to properly calculate total
                print(f"Start query: [mode=executemany] {statement} [total=?]")
            else:
                print(f"Start query: [mode=single] -> {statement}, {parameters}")


def sql_logging_disable():
    if event.contains(Engine, "before_cursor_execute", _before_cursor_execute):
        event.remove(Engine, "before_cursor_execute", _before_cursor_execute)
    if event.contains(Engine, "after_cursor_execute", _after_cursor_execute):
        event.remove(Engine, "after_cursor_execute", _after_cursor_execute)


def sql_logging_enable():
    if not event.contains(Engine, "before_cursor_execute", _before_cursor_execute):
        event.listen(Engine, "before_cursor_execute", _before_cursor_execute)
    if not event.contains(Engine, "after_cursor_execute", _after_cursor_execute):
        event.listen(Engine, "after_cursor_execute", _after_cursor_execute)
