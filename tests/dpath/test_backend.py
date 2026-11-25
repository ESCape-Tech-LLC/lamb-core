import subprocess
import sys
import unittest
from importlib import import_module
from importlib.util import find_spec

from lamb.utils import dpath, dpath_value


class DpathBackendTest(unittest.TestCase):
    def test_public_functions_use_the_installed_backend(self):
        if find_spec("_lamb_dpath_fast") is None:
            backend = import_module("lamb.utils.dpath._impl")
        else:
            backend = import_module("_lamb_dpath_fast")

        self.assertIs(dpath_value, backend.dpath_value)
        self.assertIs(dpath.dpath_value, backend.dpath_value)
        self.assertIs(dpath.adapt_dict_impl, backend.adapt_dict_impl)

    @unittest.skipUnless(find_spec("_lamb_dpath_fast"), "requires lamb[dpath-fast]")
    def test_native_module_can_be_imported_first(self):
        subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import _lamb_dpath_fast; from lamb.utils import dpath_value; "
                    "assert dpath_value is _lamb_dpath_fast.dpath_value"
                ),
            ],
            check=True,
        )
