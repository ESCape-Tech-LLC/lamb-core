from __future__ import annotations

import logging
from typing import ClassVar

import sqlalchemy.orm
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from lamb.db.session import get_metadata, lamb_db_session_maker
from lamb.utils import dpath_value
from lamb.utils.core import lazy
from lamb.utils.validators import validate_not_empty

__all__ = ["CommandError", "LambCommand", "LambCommandMixin"]

logger = logging.getLogger(__name__)


class LambCommandMixin:
    log_level: ClassVar[str | None] = None
    db_key: ClassVar[str | None] = None
    db_async: ClassVar[bool] = False

    @lazy
    def db_session(self) -> sqlalchemy.orm.Session | sqlalchemy.ext.asyncio.AsyncSession:
        return lamb_db_session_maker(db_key=self.db_key, pooled=True, sync=not self.db_async)

    @lazy
    def db_metadata(self) -> sqlalchemy.schema.MetaData:
        return get_metadata(db_key=self.db_key, pooled=True, sync=not self.db_async)

    def add_arguments(self, parser):
        # noinspection PyUnresolvedReferences
        super().add_arguments(parser)
        parser.add_argument(
            "-l",
            "--log-level",
            action="store",
            dest="log_level",
            default=None,
            help="Log level",
            type=str,
        )
        parser.add_argument(
            "-D",
            "--db-key",
            action="store",
            dest="db_key",
            default=self.db_key or "default",
            help="Database to use",
            type=str,
        )
        parser.add_argument(
            "--db-async",
            action="store_true",
            dest="db_async",
            default=self.db_async or False,
            help="Use asynchronously database session and metadata",
        )

    def execute(self, *args, **options):
        # parse log level
        log_level = options["log_level"]
        if log_level is not None and "loggers" in settings.LOGGING:
            logger_names = settings.LOGGING["loggers"].keys()
            for logger_name in logger_names:
                logging.getLogger(logger_name).setLevel(log_level)
        self.log_level = log_level

        # parse db key
        _db_key = dpath_value(options, "db_key", str, transform=validate_not_empty)
        if _db_key not in settings.LAMB_DB_CONFIG:
            raise CommandError(f"{self.__class__.__name__}. Unknown db_key={_db_key}")
        self.db_key = _db_key
        self.db_async = dpath_value(options, "db_async", bool)

        logger.info(
            f"{self.__class__.__name__}. options: db_key={self.db_key}, db_async={self.db_async}, log_level={self.log_level}"
        )

        # noinspection PyUnresolvedReferences
        super().execute(*args, **options)


class LambCommand(LambCommandMixin, BaseCommand):
    """
    Abstract management command

    """

    help = "Abstract Lamb management command"

    def handle(self, *args, **options):
        raise NotImplementedError("subclasses of BaseCommand must provide a handle() method")
