from __future__ import annotations

import logging

import sqlalchemy.orm
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from lamb.db.session import lamb_db_session_maker

__all__ = ["LambCommand", "LambLoglevelMixin", "CommandError"]

logger = logging.getLogger(__name__)


class LambLoglevelMixin:
    log_level: str | None = None
    db_session: sqlalchemy.orm.Session

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_session = lamb_db_session_maker()

    def add_arguments(self: BaseCommand, parser):
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

    def execute(self, *args, **options):
        log_level = options["log_level"]
        if log_level is not None and "loggers" in settings.LOGGING:
            logger_names = settings.LOGGING["loggers"].keys()
            for logger_name in logger_names:
                logging.getLogger(logger_name).setLevel(log_level)
        self.log_level = log_level
        # noinspection PyUnresolvedReferences
        super().execute(*args, **options)


class LambCommand(LambLoglevelMixin, BaseCommand):
    """
    Abstract management command

    """

    help = "Abstract Lamb management command"  # noqa: A003

    def handle(self, *args, **options):
        raise NotImplementedError("subclasses of BaseCommand must provide a handle() method")
