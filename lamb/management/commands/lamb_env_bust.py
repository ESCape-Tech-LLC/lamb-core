import logging
import os
import pathlib

import dotenv
import jinja2
from django.core.management.base import BaseCommand, CommandError

from lamb.management.base import LambCommandMixin
from lamb.utils import dpath_value
from lamb.utils.transformers import tf_list_string
from lamb.utils.validators import validate_not_empty

try:
    import clipboard
except ImportError:
    clipboard = None

logger = logging.getLogger(__name__)


class Command(LambCommandMixin, BaseCommand):
    help = "Command to render template from some file with env variables"

    _input_file: pathlib.Path
    _output_file: pathlib.Path | None
    _env_files: list[pathlib.Path] | None
    _clipboard: bool
    _strict: bool

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            action="store",
            dest="input_file",
            help="Path to input file",
        )
        parser.add_argument(
            "--env-file",
            action="store",
            dest="env_file",
            nargs="*",
            type=str,
            help="Path to env file - multiple files are allowed (space separated). By default would use current env variables",
        )
        parser.add_argument(
            "-o",
            "--output-file",
            action="store",
            dest="output_file",
            help="Path to output file - optional (default would output to stdout)",
            type=str,
            required=False,
        )
        parser.add_argument(
            "-c",
            "--clipboard",
            action="store_true",
            dest="clipboard",
            default=False,
            help="Copy output to clipboard (clipboard lib required)",
        )
        parser.add_argument(
            "-s",
            "--strict",
            action="store_true",
            dest="strict",
            default=False,
            help="Strict mode that requires all variables to exist (default False)",
        )

    def handle(self, *args, **options):
        # parse args
        if _env_files := dpath_value(options, "env_file", list, transform=tf_list_string, allow_none=True):
            self._env_files = [pathlib.Path(ef).absolute() for ef in _env_files]
        else:
            self._env_files = None

        self._input_file = pathlib.Path(dpath_value(options, "input_file", str))
        if not self._input_file.exists():
            raise CommandError("Input file does not exist")
        if not self._input_file.is_file():
            raise CommandError("Input file is not a file")
        self._input_file = self._input_file.absolute()

        if _output_file := dpath_value(options, "output_file", str, allow_none=True, transform=validate_not_empty):
            self._output_file = pathlib.Path(dpath_value(options, "output_file", str)).absolute()
        else:
            self._output_file = None

        self._clipboard = dpath_value(options, "clipboard", bool, default=False)
        self._strict = dpath_value(options, "strict", bool, default=False)

        logger.info(
            f"lamb_env_bust. args: "
            f"\n\tinput_file={self._input_file}"
            f"\n\toutput_file={self._output_file}"
            f"\n\tenv_files={[str(ef) for ef in self._env_files] if self._env_files else None}"
            f"\n\tclipboard={self._clipboard}"
            f"\n\tstrict={self._strict}"
        )

        # processing: load env variables
        if self._env_files:
            env_vars = {}
            for ef in self._env_files:
                env_vars.update(dotenv.dotenv_values(ef))
        else:
            env_vars = dict(os.environ)

        logger.info(f"lamb_env_bust. env_vars: {env_vars}")

        # render result
        with open(self._input_file) as f:
            data = f.read()
            engine = jinja2.Environment()
            if self._strict:
                engine.undefined = jinja2.StrictUndefined

            template = engine.from_string(data)
            result = template.render(env_vars)

        # save to file/clipboard
        if self._output_file:
            with open(self._output_file, "w") as f:
                f.write(result)
                logger.info(f"lamb_env_bust. wrote output: {self._output_file}")
        else:
            logger.info(result)

        if self._clipboard:
            if clipboard is None:
                raise CommandError("clipboard is required")
            clipboard.copy(result)
