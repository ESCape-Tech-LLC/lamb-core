# -*- coding: utf-8 -*-
__author__ = 'KoNEW'


from importlib import import_module
from django.core.management.base import CommandError, LabelCommand
from sqlalchemy.exc import SQLAlchemyError, DBAPIError
from lamb.db.session import metadata, _engine

from sqlalchemy.schema import DropTable, DropSequence
from sqlalchemy.ext.compiler import compiles


@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    return compiler.visit_drop_table(element) + " CASCADE"


@compiles(DropSequence, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    return compiler.visit_drop_sequence(element) + ' CASCADE'


class Command(LabelCommand):
    help = 'Creates database table for provided modules'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--force',
                            action='store_true',
                            dest='force',
                            default=False,
                            help='Force drop all before create')

    def handle_label(self, label, **options):
        try:
            import_module(label)
            if options['force']:
                metadata.drop_all()
            metadata.create_all()
        except ImportError as e:
            print(e)
            raise CommandError('Failed to import module. \"%s\"' % e)
        except (SQLAlchemyError, DBAPIError) as e:
            print(e)
            raise CommandError('Database error occurred. \"%s\"' % e)
