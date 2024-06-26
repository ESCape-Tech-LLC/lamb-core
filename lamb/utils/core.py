# core level utils - should not depend on any other lamb modules to omit circular references
from __future__ import annotations

import copy
import types
import random
import string
import warnings
import importlib
import urllib.parse
from typing import TypeVar

__all__ = [
    "DeprecationClassHelper",
    "DeprecationClassMixin",
    "compact",
    "import_by_name",
    "random_string",
    "masked_url",
    "masked_dict",
    "get_redis_url",
    "list_chunks",
]

from typing import Any, Dict, List, Union, Optional, Generator

import furl


class DeprecationClassHelper(object):
    # WARN: actually or work as expected - use mixin
    def __init__(self, new_target):
        self.new_target = new_target

    def _warn(self):
        warnings.warn(f"Class is deprecated, use {self.new_target} instead", DeprecationWarning, stacklevel=3)

    def __call__(self, *args, **kwargs):
        self._warn()
        return self.new_target(*args, **kwargs)

    def __getattr__(self, attr):
        self._warn()
        return getattr(self.new_target, attr)


class DeprecationClassMixin:

    def __init__(self):
        try:
            target_cls = self.__class__.__bases__[-1]
            msg = f"Class {self.__class__.__name__} is deprecated, use {target_cls.__name__} instead"
        except Exception:
            msg = f"Class {self.__class__.__name__} is deprecated"

        warnings.warn(msg, DeprecationWarning, stacklevel=1)


def compact(*args, traverse: bool = False, collapse: bool = False) -> Union[list, dict, tuple]:
    """Compact version of container
    :param traverse: Boolean flag for recursive container lookup
    :param collapse: Boolean flag for remove child containers in traverse mode if length is 0
    """
    # check variadic
    if len(args) == 1:
        obj = args[0]
    else:
        obj = tuple(args)

    # recursive traverse
    def _traverse(_o):
        if not traverse or not isinstance(_o, (list, tuple, dict)):
            return _o
        else:
            _o = compact(_o, traverse=traverse, collapse=collapse)
            if len(_o) == 0 and collapse:
                return None
            return _o

    # compacting
    if isinstance(obj, list):
        result = [_traverse(o) for o in obj if o is not None]
    elif isinstance(obj, tuple):
        result = tuple([_traverse(o) for o in obj if o is not None])
    elif isinstance(obj, dict):
        result = {k: _traverse(v) for k, v in obj.items() if v is not None}
    else:
        result = obj

    # collapse - apply only after main compacting to omit double processing and leave top level object stable
    if collapse:
        result = compact(result)

    return result


def import_by_name(name: str):
    # try to import as module
    def _import_module(_name) -> Optional[types.ModuleType]:
        try:
            return importlib.import_module(_name)
        except ImportError:
            return None

    res = _import_module(name)
    if res is None:
        module, _, func_or_class = name.rpartition(".")
        mod = _import_module(module)
        try:
            res = getattr(mod, func_or_class)
        except AttributeError as e:
            raise ImportError(f"Could not load {name}") from e

    return res


def random_string(length: int = 10, char_set: str = string.ascii_letters + string.digits) -> str:
    """Generate random string

    :param length: Length of string to generate, by default 10
    :param char_set: Character set as string to be used as source for random, by default alphanumeric
    """
    result = ""
    for _ in range(length):
        result += random.choice(char_set)
    return result


def masked_dict(dct: Dict[Any, Any], *masking_keys) -> Dict[Any, Any]:
    return {k: v if k not in masking_keys else "*****" for k, v in dct.items()}


def masked_url(u: Union[furl.furl, str]) -> str:
    if isinstance(u, str):
        u = furl.furl(u)
    _u = copy.deepcopy(u)
    _u.password = "*****"
    return urllib.parse.unquote(_u.url)


CT = TypeVar("CT")


def list_chunks(lst: List[CT], n: int) -> Generator[List[CT], None, None]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def get_redis_url(
    host: str = "localhost",
    port: int = 6379,
    password: str = None,
    db: int = 0,
    username: Optional[str] = None,
) -> str:
    result = furl.furl()
    result.scheme = "redis"
    result.host = host
    result.port = port
    if password is not None and len(password) > 0:
        result.password = password
    if username is not None and len(username) > 0:
        result.username = username
    result.path.add(str(db))
    return result.url
