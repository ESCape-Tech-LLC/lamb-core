from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from django.conf import settings
from django.http import HttpResponse

import lazy_object_proxy

try:
    import ujson
except ImportError:
    ujson = None

# Lamb Framework
from lamb import exc
from lamb.utils import dpath_value, import_by_name

__all__ = ["JsonResponse"]

logger = logging.getLogger(__name__)


# TODO: вполне вероятно в питоне 3.10 это все вот нахер не нужно - он и в стандартном модуле нормально оптимизируется
# utils and choose engine
def _get_encoder_class():
    class_module_path = settings.LAMB_RESPONSE_ENCODER
    result = import_by_name(class_module_path)
    logger.debug(f"LAMB_RESPONSE_ENCODER: encoder would be used {class_module_path} -> {result}")
    return result


def _impl_json(data: Any, encoder: json.JSONEncoder, indent: Optional[int]) -> Any:
    if indent is not None:
        return json.dumps(
            data,
            indent=indent,
            ensure_ascii=False,
            default=encoder.default,
            sort_keys=False,
        )
    else:
        return json.dumps(
            data,
            ensure_ascii=False,
            default=encoder.default,
            sort_keys=False,
        )


def _impl_ujson(data: Any, encoder: json.JSONEncoder, indent: Optional[int]) -> Any:
    if indent is not None:
        return json.dumps(
            data,
            indent=indent,
            ensure_ascii=False,
            default=encoder.default,
            sort_keys=False,
        )
    else:
        return json.dumps(
            data,
            ensure_ascii=False,
            default=encoder.default,
            sort_keys=False,
        )


def _get_dump_engine() -> Callable[[Any, json.JSONEncoder, Optional[int]], Any]:
    settings_engine: Optional[str] = dpath_value(
        settings,
        "LAMB_RESPONSE_JSON_ENGINE",
        str,
        allow_none=True,
    )
    logger.debug(f"LAMB_RESPONSE_JSON_ENGINE: settings value -> {settings_engine}")

    if settings_engine is None:
        if ujson is not None:
            result = _impl_ujson
        else:
            result = _impl_json
    else:
        try:
            # settings enforced
            settings_engine = settings_engine.lower()
            if settings_engine == "ujson":
                result = _impl_ujson
                module = ujson
            elif settings_engine == "json":
                result = _impl_json
                module = json
            else:
                raise exc.ImproperlyConfiguredError(f"Unknown LAMB_RESPONSE_JSON_ENGINE: {settings_engine}")

            # check module exist
            if module is None:
                raise exc.ImproperlyConfiguredError(
                    f"Could not load LAMB_RESPONSE_JSON_ENGINE module: {settings_engine}"
                )
        except exc.ImproperlyConfiguredError as e:
            logger.critical(f"LAMB_RESPONSE_JSON_ENGINE: Fall-down to default encoder: {e}")
            result = _impl_json

    logger.debug(f"LAMB_RESPONSE_JSON_ENGINE: engine would be used -> {result}")
    return result


# constants
_JSON_ENCODER_CLASS = lazy_object_proxy.Proxy(_get_encoder_class)
_JSON_DUMP_IMPL = lazy_object_proxy.Proxy(_get_dump_engine)
_JSON_CONTENT_TYPE = "application/json; charset=utf8"


class JsonResponse(HttpResponse):
    def __init__(self, data=None, status=200, callback=None, request=None, **kwargs):
        # determine content_type
        super().__init__(content_type=_JSON_CONTENT_TYPE, status=status, **kwargs)

        if data is not None:
            # encode response in form of json
            encoder = _JSON_ENCODER_CLASS(callback, request)

            content = _JSON_DUMP_IMPL(
                data=data,
                encoder=encoder,
                indent=settings.LAMB_RESPONSE_JSON_INDENT,
            )

            # return result
            self.content = content

    @staticmethod
    def encode_object(obj, callback: Optional[Callable] = None, request: Optional[object] = None, **kwargs):
        encoder = _JSON_ENCODER_CLASS(callback, request, **kwargs)
        result = _JSON_DUMP_IMPL(
            data=obj,
            encoder=encoder,
            indent=settings.LAMB_RESPONSE_JSON_INDENT,
        )
        return result
