# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

import logging

from importlib import import_module
from django.core.management.base import CommandError, LabelCommand
from sqlalchemy.exc import SQLAlchemyError, DBAPIError
from sqlalchemy.schema import DropTable, DropSequence
from sqlalchemy.ext.compiler import compiles

from lamb.db.session import metadata
from lamb.management.base import LambLoglevelMixin
from lamb.utils import compact

logger = logging.getLogger(__name__)


@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **_):
    return compiler.visit_drop_table(element) + " CASCADE"


@compiles(DropSequence, "postgresql")
def _compile_drop_table(element, compiler, **_):
    return compiler.visit_drop_sequence(element) + ' CASCADE'


class Command(LambLoglevelMixin, LabelCommand):
    help = 'Creates database table for provided modules'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            default=False,
            help='Force drop all before create'
        )
        parser.add_argument(
            '--exclude-tables',
            action='store',
            dest='exclude_tables',
            default=None,
            help='Tables to exclude from creation process'
        )

    def handle_label(self, label, **options):
        try:
            import_module(label)
            if options['exclude_tables'] is not None:
                exclude_tables = options['exclude_tables'].split(',')
                tables = [v for k, v in metadata.tables.items() if k not in exclude_tables]
            else:
                tables = None
            kwargs = {'tables': tables}
            kwargs = compact(kwargs)

            if options['force']:
                metadata.drop_all(**kwargs)

            metadata.create_all(**kwargs)
            # if options['exclude_tables'] is not None:
            #     exclude_tables=options['exclude_tables'].split(',')
            #     tables = {k: v for k, v in metadata.tables.items() if k not in exclude_tables}
            #     metadata.create_all(tables=tables.values())
            # else:
            #     metadata.create_all()
        except ImportError as e:
            logging.warning('Module import failed: %s' % e)
            raise CommandError('Failed to import module. \"%s\"' % e)
        except (SQLAlchemyError, DBAPIError) as e:
            logger.warning('Database commit failed: %s' % e)
            raise CommandError('Database error occurred. \"%s\"' % e)
