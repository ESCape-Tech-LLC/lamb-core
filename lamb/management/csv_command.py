from __future__ import annotations

import csv
import io
import logging
import pathlib
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from itertools import islice
from typing import IO, Any

from lamb.exc import InvalidParamValueError
from lamb.service.aws.utils import s3_download_file_sync, s3_filepath_parse
from lamb.utils import dpath_value
from lamb.utils.validators import validate_not_empty

__all__ = ["CsvCommandMixin"]

logger = logging.getLogger(__name__)


# TODO: add csv sniffer to auto extract delimiter, line-break and quote info
class CsvCommandMixin:
    help = "Base command mixin for CSV files processing"

    _default_file_path: str = None

    input_file: str
    delimiter: str
    quote_char: str
    cleanup: bool
    encoding: str

    # utils
    @property
    def _default_file_help(self) -> str | None:
        if self._default_file_path:
            return f"File to process info (default - {self._default_file_path})"
        else:
            return None

    @contextmanager
    def _open_file(self) -> Generator[IO[str]]:
        """Discover actual file type and return path to local copy"""
        tmp_file = None
        file_path = None
        f = None
        try:
            if isinstance(self.input_file, str) and self.input_file.startswith("s3:"):
                s3_file_url, _ = s3_filepath_parse(str(self.input_file))
                tmp_file = tempfile.NamedTemporaryFile(delete_on_close=False)  # noqa: SIM115
                file_path = pathlib.Path(tmp_file.name)
                tmp_file.close()
                s3_download_file_sync(s3_file_path=s3_file_url.url, output_file_path=file_path)
                logger.info(f"<{self.__class__.__name__}:_open_file> Did open: mode=S3, path={tmp_file.name=}")
            else:
                file_path = pathlib.Path(self.input_file).absolute()
                if not file_path.exists():
                    raise InvalidParamValueError(f"file not exist: {file_path}")
                if not file_path.is_file():
                    raise InvalidParamValueError(f"object under provided path is not file: {file_path}")
                logger.info(f"<{self.__class__.__name__}:_open_file> Did open: mode=local, path={file_path}")

            f = open(file_path, encoding=self.encoding)  # noqa: SIM115 - возможно получится убрать
            yield f
        finally:
            if f is not None:
                f.close()
                logger.debug(f"<{self.__class__.__name__}:_open_file> File descriptor closed")
            if tmp_file and file_path and file_path.exists():
                file_path.unlink()
                logger.info(f"<{self.__class__.__name__}:_open_file> Cleaned up temporary {file_path=}")

    # legacy
    @property
    def reader(self) -> csv.DictReader:
        """Legacy version - reader over full loaded StringIO"""
        return csv.DictReader(f=self.data_stream, delimiter=self.delimiter, quotechar=self.quote_char)

    @property
    def data_stream(self) -> io.StringIO:
        """Legacy version with full file load in memory and StringIO output"""
        with self._open_file() as f:
            data = f.read()

        return io.StringIO(data)

    def dict_stream_reader(self) -> Generator[dict[str, Any]]:
        """Generator over file rows"""
        with self._open_file() as f:
            reader = csv.DictReader(f=f, delimiter=self.delimiter, quotechar=self.quote_char)
            yield from reader

    def dict_stream_reader_batched(self, batch_size: int) -> Generator[list[dict[str, Any]]]:
        """Generator over file rows in batches"""
        with self._open_file() as f:
            index = 0
            reader = csv.DictReader(f=f, delimiter=self.delimiter, quotechar=self.quote_char)
            while True:
                batch = list(islice(reader, batch_size))
                if not batch:
                    logger.debug(
                        f"<{self.__class__.__name__}:dict_stream_reader_batched> batch extract: {index=}, count=0 -> FINISH"
                    )
                    break
                index += 1
                logger.debug(
                    f"<{self.__class__.__name__}:dict_stream_reader_batched> batch extract: {index=}, count={len(batch)} -> CONTINUE"
                )
                yield batch

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
        parser.add_argument(
            "--encoding",
            action="store",
            dest="encoding",
            default="utf-8",
            help="CSV file encoding (default - utf-8)",
        )

    def parse_csv_options(self, *args, **options):
        self.input_file = dpath_value(options, "input_file", str, transform=validate_not_empty)
        self.delimiter = dpath_value(options, "delimiter", str, transform=validate_not_empty)
        self.quote_char = dpath_value(options, "quote_char", str, transform=validate_not_empty)
        self.encoding = dpath_value(options, "encoding", str, transform=validate_not_empty)
        self.cleanup = dpath_value(options, "cleanup", bool)
