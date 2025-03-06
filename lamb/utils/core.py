# core level utils - should not depend on any other lamb modules to omit circular references
from __future__ import annotations

import copy
import functools
import importlib
import random
import string
import types
import urllib.parse
import warnings
from collections.abc import Generator
from types import GenericAlias
from typing import Any, TypeVar

import furl

__all__ = [
    "DeprecationClassHelper",
    "DeprecationClassMixin",
    "compact",
    "import_by_name",
    "random_string",
    "masked_url",
    "masked_dict",
    "masked_string",
    "get_redis_url",
    "list_chunks",
    "lazy",
    "lazy_ro",
    "lazy_default",
    "lazy_default_ro",
    "class_or_instance_method",
]


class DeprecationClassHelper:
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
    def __init__(self, *args, **kwargs):
        try:
            target_cls = self.__class__.__bases__[-1]
            msg = f"Class {self.__class__.__name__} is deprecated, use {target_cls.__name__} instead"
        except Exception:
            msg = f"Class {self.__class__.__name__} is deprecated"

        warnings.warn(msg, DeprecationWarning, stacklevel=1)

        super().__init__(*args, **kwargs)


def compact(*args, traverse: bool = False, collapse: bool = False) -> list | dict | tuple:
    """Compact version of container
    :param traverse: Boolean flag for recursive container lookup
    :param collapse: Boolean flag for remove child containers in traverse mode if length is 0
    """
    # check variadic
    obj = args[0] if len(args) == 1 else tuple(args)

    # recursive traverse
    def _traverse(_o):
        if not traverse or not isinstance(_o, list | tuple | dict):
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
    def _import_module(_name) -> types.ModuleType | None:
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


CT = TypeVar("CT")


def list_chunks(lst: list[CT], n: int) -> Generator[list[CT], None, None]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def get_redis_url(
    host: str = "localhost",
    port: int = 6379,
    password: str = None,
    db: int = 0,
    username: str | None = None,
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


# maskers
def masked_dict(dct: dict[Any, Any] | None, *masking_keys) -> dict[Any, Any] | None:
    if dct is None:
        return None
    masking_keys = [mk.lower() if isinstance(mk, str) else mk for mk in masking_keys]
    return {k: v if (k.lower() if isinstance(k, str) else k) not in masking_keys else "*****" for k, v in dct.items()}


def masked_url(u: furl.furl | str, hide_none_pass: bool = False) -> str:
    if u is None:
        return None

    if isinstance(u, str):
        u = furl.furl(u)
    _u = copy.deepcopy(u)

    if _u.password is not None or hide_none_pass:
        _u.password = "*****"

    return urllib.parse.unquote(_u.url)


def masked_string(v: str | None) -> str | None:
    if v is None:
        return None

    return "*****"


# descriptors
class class_or_instance_method(classmethod):
    def __get__(self, instance, type_):
        descr_get = super().__get__ if instance is None else self.__func__.__get__
        return descr_get(instance, type_)


# lazy utils
_lazy_marker = object()


class lazy:
    """Lazy descriptor.

    Inspired by https://pypi.org/project/lazy/ project.

    Could be used as drop-in replacement for original project version. Cause __set__ and __delete__
    methods not implemented and underlying data stored in __dict__ - it acts like pure lazy evaluated attribute
    of instance and value can be changed via with direct access

    Usage::

        from lamb.utils.core import lazy

        def check(cls, l_cls):
            a = cls()

            print(f'usage 1: {a.some_val}')
            print(f'usage 2: {a.some_val}')

            a.some_val = 12
            print(f'after set: {a.some_val}')

            del a.some_val
            print(f'after del: {a.some_val}')

            l_cls.invalidate(a, 'some_val')
            print(f'after invalidate: {a.some_val}')

        class A:
            _val: int = 0
            @lazy
            def some_val(self) -> int:
                self._val += 1
                return self._val

        >> usage 1: 1
        >> usage 2: 1
        >> after set: 12
        >> after del: 2
        >> after invalidate: 3

    """

    def __init__(self, func):
        self.__func = func
        functools.wraps(self.__func)(self)

    __class_getitem__ = classmethod(GenericAlias)

    def __set_name__(self, owner, name):
        self.__name__ = name

    def _get_name(self, inst, owner):
        if not hasattr(inst, "__dict__"):
            raise AttributeError(f"'{owner.__name__}' object has no attribute '__dict__'")

        name = self.__name__
        if name.startswith("__") and not name.endswith("__"):
            name = f"_{owner.__name__}{name}"

        return name

    def __get__(self, inst, owner):
        """Get lazy attribute or calculate on first usage"""
        if inst is None:
            return self

        name = self._get_name(inst, owner)

        value = inst.__dict__.get(name, _lazy_marker)
        if value is _lazy_marker:
            inst.__dict__[name] = value = self.__func(inst)
        return value

    @classmethod
    def invalidate(cls, inst, name):
        """Invalidate a lazy attribute with class level operation"""
        owner = inst.__class__

        if not hasattr(inst, "__dict__"):
            raise AttributeError(f"{owner.__name__}' object has no attribute '__dict__'")

        if name.startswith("__") and not name.endswith("__"):
            name = f"_{owner.__name__}{name}"

        if not isinstance(getattr(owner, name), cls):
            raise AttributeError(f"{owner.__name__}.{name}' is not a {cls.__name__} attribute")

        if name in inst.__dict__:
            del inst.__dict__[name]


class lazy_ro(lazy):
    """Read only lazy descriptor

    Overrides __set__ and __delete__ methods to disable attribute modifications.

    Usage::

        def check(cls, l_cls):
            a = cls()

            print(f'usage 1: {a.some_val}')
            print(f'usage 2: {a.some_val}')

            a.some_val = 12
            print(f'after set: {a.some_val}')

            del a.some_val
            print(f'after del: {a.some_val}')

            l_cls.invalidate(a, 'some_val')
            print(f'after invalidate: {a.some_val}')

        class A:
            _val: int = 0
            @lazy_ro
            def some_val(self) -> int:
                self._val += 1
                return self._val

        >> usage 1: 1
        >> usage 2: 1
        >> after set: 1
        >> after del: 1
        >> after invalidate: 2

    """

    def __set__(self, instance, value):
        pass

    def __delete__(self, instance):
        pass


def lazy_default(default):
    """Lazy evaluated descriptor with default support

    If underlying function fall with exception would return default value.
    After first success calculation value would be memoized in instance dict.

    NB: Current implementation disables invalidate classmethod cause wrapped in decorator.

    Usage::

        def check_default(cls):
            a = cls()

            for i in range(0, 10):
                print(f'usage {i+1:2d}: {a.some_val}')

            a.some_val = 12
            print(f'after set: {a.some_val}')

            del a.some_val
            print(f'after del: {a.some_val}')


        class A:
            _val: int = 0
            @lazy_default(default=-1)
            def some_val(self) -> int:
                self._val += 1
                if self._val >= 5:
                    return self._val
                else:
                    raise ValueError

        >> usage  1: -1
        >> usage  2: -1
        >> usage  3: -1
        >> usage  4: -1
        >> usage  5: 5
        >> usage  6: 5
        >> usage  7: 5
        >> usage  8: 5
        >> usage  9: 5
        >> usage 10: 5
        >> after set: 12
        >> after del: 6

    """

    def wrap(func):
        class _lazy(lazy):
            def __get__(self, inst, owner):
                """Get lazy attribute or return default on exception"""
                if inst is None:
                    return self

                name = self._get_name(inst, owner)

                value = inst.__dict__.get(name, _lazy_marker)
                if value is _lazy_marker:
                    try:
                        inst.__dict__[name] = value = self.__func(inst)
                    except Exception:
                        value = default

                return value

        return _lazy(func)

    return wrap


def lazy_default_ro(default):
    """Lazy evaluated descriptor with default support and read-only logic

    If underlying function fall with exception would return default value.
    After first success calculation value would be memoized in instance dict.

    NB: Current implementation disables invalidate classmethod cause wrapped in decorator.

    Usage::

        def check_default(cls):
            a = cls()

            for i in range(0, 10):
                print(f'usage {i+1:2d}: {a.some_val}')

            a.some_val = 12
            print(f'after set: {a.some_val}')

            del a.some_val
            print(f'after del: {a.some_val}')


        class A:
            _val: int = 0
            @lazy_default_ro(default=-1)
            def some_val(self) -> int:
                self._val += 1
                if self._val >= 5:
                    return self._val
                else:
                    raise ValueError

        >> usage  1: -1
        >> usage  2: -1
        >> usage  3: -1
        >> usage  4: -1
        >> usage  5: 5
        >> usage  6: 5
        >> usage  7: 5
        >> usage  8: 5
        >> usage  9: 5
        >> usage 10: 5
        >> after set: 5
        >> after del: 5

    """

    def wrap(func):
        class _lazy(lazy_ro):
            def __get__(self, inst, owner):
                """Get lazy attribute or return default on exception"""
                if inst is None:
                    return self

                name = self._get_name(inst, owner)

                value = inst.__dict__.get(name, _lazy_marker)
                if value is _lazy_marker:
                    try:
                        inst.__dict__[name] = value = self.__func(inst)
                    except Exception:
                        value = default

                return value

        return _lazy(func)

    return wrap
