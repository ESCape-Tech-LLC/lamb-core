from __future__ import annotations

import logging
import os
import pathlib

import jinja2
from sqlalchemy import text

from lamb.db.session import lamb_db_session_maker
from lamb.management.base import CommandError, LambCommand
from lamb.utils import dpath_value
from lamb.utils.validators import validate_not_empty

logger = logging.getLogger(__name__)


class Command(LambCommand):
    help = "Support script for plain SQL scripts running over configured databases"  # noqa: A003

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-f",
            "--migration-file",
            action="store",
            dest="migration_file",
            help="Migration file to run",
            required=True,
            type=str,
        )
        parser.add_argument(
            "--autocommit",
            action="store_true",
            dest="autocommit",
            help="Let script custom transaction management",
            required=False,
            default=False,
        )
        parser.add_argument(
            "--split",
            action="store_true",
            dest="split",
            help="Split commands in autocommit mode",
            required=False,
            default=False,
        )
        parser.add_argument(
            "--db-key",
            action="store",
            dest="db_key",
            help="Database key to process query",
            required=False,
            type=str,
            default="default",
        )
        parser.add_argument(
            "--env-bust",
            action="store_true",
            dest="env_bust",
            help="Flag to bust migration file with environment variables (jinja engine used)",
            default=False,
        )

    def handle(self, *args, **options):
        db_key = dpath_value(options, "db_key", str, transform=validate_not_empty)
        self.db_session = lamb_db_session_maker(db_key=db_key)
        migration_file_path: pathlib.Path = pathlib.Path(options["migration_file"])
        if not migration_file_path.exists():
            raise CommandError(f"File not exist: {migration_file_path}")
        if not migration_file_path.is_file():
            raise CommandError(f"Object at path is not file: {migration_file_path}")

        with open(migration_file_path, "r") as f:
            _STMT = f.read()
            env_bust = dpath_value(options, "env_bust", bool, default=False)
            if env_bust:
                template = jinja2.Template(_STMT)
                _STMT = template.render(os.environ)
                logger.debug(f"migration after template render: {_STMT}")

        if not options["autocommit"]:
            logger.info("apply migration. mode usual")
            self.db_session.execute(text(_STMT))
            self.db_session.commit()
        else:
            # касательно всей ветки этой
            # - почему и во имя чего, мистер Андерсон - я уже достоверно не помню
            # - вроде как это было нужно для скриптов лютых с подавлением автоматического эмита транзакций
            logger.info("apply migration.  mode autocommit")
            self.db_session.execute(text("ROLLBACK"))
            autocommit_engine = self.db_session.bind.execution_options(isolation_level="AUTOCOMMIT")
            cursor = autocommit_engine.raw_connection().cursor()
            cursor.execute("COMMIT;")

            if options["split"]:
                stmt_list = _STMT.split(";")
                for s in stmt_list:
                    s = s.strip()
                    if len(s.strip()) == 0 or s.startswith("--"):
                        continue
                    logger.info(f"try execute: {s}")
                    cursor.execute(s)
            else:
                logger.debug(f"try execute: {_STMT}")
                cursor.execute(_STMT)
            cursor.execute("COMMIT;")
        logger.info(f"Did apply migration: {migration_file_path}")
