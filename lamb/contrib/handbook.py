import logging
from typing import Any

from lamb import exc
from lamb.json.mixins import ResponseEncodableMixin
from lamb.utils import LambRequest
from lamb.utils.core import class_or_instance_method

logger = logging.getLogger(__name__)


__all__ = ["HandbookMixin", "HandbookEnumMixin"]


class HandbookMixin(ResponseEncodableMixin):
    """
    Base handbook mixin/protocol - expects that underlying object contains value(id)+title fields
    TODO: check to realize in form of real protocol with encode support
    """

    __attrs__: list[str] | tuple[str] = "id"
    __handbook_attrs__: list[str] | tuple[str] = None

    def response_encode(self, _: LambRequest | None = None) -> Any:
        # as part of object - return id only
        return getattr(self, self.__attrs__[0])

    def handbook_encode(self, _: LambRequest | None = None) -> dict:
        # as part of class itself - return full description
        response_attrs = self.__handbook_attrs__ or self.__attrs__
        return {attr_name: getattr(self, attr_name) for attr_name in response_attrs}


class HandbookEnumMixin(HandbookMixin):
    """Special version of handbooks based on enums"""

    __attrs__ = ("id", "title")

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        # obj.__post_new__(*args, **kwargs)
        return obj

    def __init__(self, *args, **kwargs) -> None:
        if len(args) != len(self.__class__.__attrs__):
            logger.critical(
                f"Expected attributes length not equal to received: __attrs__={self.__attrs__}, args={args}"
            )
            raise exc.ProgrammingError
        for idx, attr_title in enumerate(self.__attrs__):
            setattr(self, attr_title, args[idx])

    @class_or_instance_method
    def response_encode(self, request: LambRequest | None = None) -> Any:
        if isinstance(self, type):
            cls = self
            return [i.handbook_encode(request) for i in cls.__members__.values()]
        else:
            return super().response_encode(request)
