"""Select the installed dpath implementation once, including its dict engine."""

try:
    import _lamb_dpath_fast as _backend
except ModuleNotFoundError as error:
    if error.name != "_lamb_dpath_fast":
        raise
    from . import _impl as _backend

__all__ = ["adapt_dict_impl", "dpath_value"]

adapt_dict_impl = _backend.adapt_dict_impl
dpath_value = _backend.dpath_value


def __getattr__(name):
    # Forward lookups such as _impl_dict to the backend that owns the current engine.
    return getattr(_backend, name)
