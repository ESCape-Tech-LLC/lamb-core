from __future__ import annotations

import logging
import pathlib

# Lamb Framework
from lamb.utils import dpath_value
from lamb.db.session import lamb_db_session_maker
from lamb.management.base import LambCommand, CommandError
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

    def handle(self, *args, **options):
        db_key = dpath_value(options, "db_key", str, transform=validate_not_empty)
        self.db_session = lamb_db_session_maker(db_key=db_key)
        migration_file_path: pathlib.Path = pathlib.Path(options["migration_file"])
        if not migration_file_path.exists():
            raise CommandError(f"File not exist: {migration_file_path}")
        if not migration_file_path.is_file():
            raise CommandError(f"Object at path is not file: {migration_file_path}")
        # migration_file_path = pathlib.Path(settings.BASE_DIR).joinpath("migrations_sql").joinpath(migration_file)
        with open(migration_file_path, "r") as f:
            _STMT = f.read()

        if not options["autocommit"]:
            logger.info("run_migration. mode usual")
            self.db_session.execute(_STMT)
            self.db_session.commit()
        else:
            # касательно всей ветки этой
            # - почему и во имя чего, мистер Андерсон - я уже достоверно не помню
            # - вроде как это было нужно для скриптов лютых с подавлением автоматического эмита транзакций
            logger.info("run_migration. mode autocommit")
            self.db_session.execute("ROLLBACK")
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
                logger.info(f"try execute: {_STMT}")
                cursor.execute(_STMT)
            cursor.execute("COMMIT;")
        logger.info(f"Did apply migration: {migration_file_path}")
