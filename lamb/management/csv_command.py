from __future__ import annotations

import csv
import io
import logging
import pathlib
from functools import partial

from lamb.exc import InvalidParamValueError
from lamb.utils import dpath_value
from lamb.utils.validators import validate_length, validate_not_empty

__all__ = ["CsvCommandMixin"]

logger = logging.getLogger(__name__)


# TODO: add csv sniffer to auto extract delimiter, line-break and quote info
class CsvCommandMixin:
    help = "Base command mixin for CSV files processing"  # noqa: A003

    _default_file_path: str = None
    _input_file: str
    delimiter: str
    quote_char: str
    cleanup: bool

    @property
    def _default_file_help(self) -> str | None:
        if self._default_file_path:
            return f"File to process info (default - {self._default_file_path})"
        else:
            return

    @property
    def reader(self) -> csv.DictReader:
        return csv.DictReader(f=self.data_stream, delimiter=self.delimiter, quotechar=self.quote_char)

    @property
    def data_stream(self) -> io.StringIO:
        # TODO разузнать зачем был функционал извлечения из s3
        file_path = pathlib.Path(self._input_file).absolute()
        if not file_path.exists():
            raise InvalidParamValueError(f"file not exist: {file_path}")
        if not file_path.is_file():
            raise InvalidParamValueError(f"object under provided path is not file: {file_path}")

        with open(file_path) as f:
            result = io.StringIO()
            result.write(f.read())
            result.seek(0)
            return result

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--cleanup",
            action="store_true",
            dest="cleanup",
            default=False,
            help="Cleanup database data before load",
        )
        parser.add_argument(
            "--file",
            "-f",
            action="store",
            dest="input_file",
            default=self._default_file_path,
            help=self._default_file_help,
        )
        parser.add_argument(
            "--delimiter",
            "-d",
            action="store",
            dest="delimiter",
            default=";",
            help="CSV file delimiter value (default - ;)",
        )
        parser.add_argument(
            "--quote-char",
            "-q",
            action="store",
            dest="quote_char",
            default='"',
            help='CSV quote symbol value (default - ")',
        )

    def handle(self, *args, **options):
        # parse options
        self._input_file = dpath_value(
            options,
            "input_file",
            str,
            transform=validate_not_empty,
        )

        self.delimiter = dpath_value(
            options,
            "delimiter",
            str,
            transform=partial(validate_length, max_length=1, min_length=1),
        )
        self.quote_char = dpath_value(
            options,
            "quote_char",
            str,
            transform=partial(validate_length, max_length=1, min_length=1),
        )
        self.cleanup = dpath_value(
            options,
            "cleanup",
            bool,
        )
