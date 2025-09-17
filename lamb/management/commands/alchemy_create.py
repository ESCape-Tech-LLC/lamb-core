import logging
from importlib import import_module

from django.core.management.base import CommandError, LabelCommand
from sqlalchemy.dialects.postgresql import DropEnumType
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import DropSequence, DropTable

from lamb.management.base import LambCommandMixin
from lamb.utils.core import compact

logger = logging.getLogger(__name__)


@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **_):
    return compiler.visit_drop_table(element) + " CASCADE"


@compiles(DropSequence, "postgresql")
def _compile_drop_sequence(element, compiler, **_):
    return compiler.visit_drop_sequence(element) + " CASCADE"


@compiles(DropEnumType, "postgresql")
def _compile_drop_type(element, compiler, **_):
    return compiler.visit_drop_enum_type(element) + " CASCADE"


class Command(LambCommandMixin, LabelCommand):
    help = "Creates database table for provided modules"  # noqa: A003

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            default=False,
            help="Force drop all before create",
        )
        parser.add_argument(
            "--exclude-tables",
            action="store",
            dest="exclude_tables",
            default=None,
            help="Tables to exclude from creation process",
        )

    def handle_label(self, label, **options):
        try:
            metadata = self.db_metadata
            import_module(label)  # loading models

            if options["exclude_tables"] is not None:
                exclude_tables = options["exclude_tables"].split(",")
                tables = [v for k, v in metadata.tables.items() if k not in exclude_tables]
            else:
                tables = None
            kwargs = {"tables": tables, "bind": metadata.bind}
            kwargs = compact(kwargs)

            if options["force"]:
                metadata.drop_all(**kwargs)

            metadata.create_all(**kwargs)
        except ImportError as e:
            logging.warning(f"Module import failed: {e}")
            raise CommandError(f'Failed to import module. "{e}"') from e
        except (SQLAlchemyError, DBAPIError) as e:
            logger.warning(f"Database commit failed: {e}")
            raise CommandError(f'Database error occurred. "{e}"') from e
