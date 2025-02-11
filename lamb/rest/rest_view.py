from __future__ import annotations

import json
import logging
from functools import update_wrapper
from typing import Union

from django.utils.decorators import classonlymethod
from sqlalchemy.ext.asyncio import AsyncSession as SAAsyncSession
from sqlalchemy.orm import Session as SASession

from lamb.exc import InvalidBodyStructureError, NotRealizedMethodError
from lamb.utils import (
    CONTENT_ENCODING_MULTIPART,
    dpath_value,
    get_request_accept_encoding,
    get_request_body_encoding,
    parse_body_as_json,
)
from lamb.utils.core import lazy

logger = logging.getLogger(__name__)

__all__ = ["RestView"]


class RestView:
    """Abstract class for dispatching url requests in REST logic

    Class works in a similar way to django class based views to dispatch http methods.

    Attributes:
        request (HttpRequest): Http request of view
    """

    __default_db__ = "default"

    def __init__(self, **kwargs):
        """
        Constructor. Called in the URLconf; can contain helpful extra
        keyword arguments, and other things.
        """
        # assign for proper type hints
        self.request = None

        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classonlymethod
    def as_request_callable(cls):
        """Main entry point for a request-response process."""

        def view(request, *args, **kwargs):
            instance = cls()
            instance.request = request
            instance.args = args
            instance.kwargs = kwargs
            return instance.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view

    def dispatch(self, request, *args, **kwargs):
        handler = getattr(self, request.method.lower(), self.http_method_not_realized)
        return handler(request, *args, **kwargs)

    @lazy
    def request_content_type(self) -> str:
        return get_request_body_encoding(self.request)

    @lazy
    def response_content_type(self) -> str:
        return get_request_accept_encoding(self.request)

    @lazy
    def parsed_body(self) -> dict | list:
        content_type = self.request_content_type
        logger.debug(f"Lamb:RestView. Request body encoding discovered: {content_type}")

        if content_type == CONTENT_ENCODING_MULTIPART:
            payload = dpath_value(self.request.POST, "payload", str)
            try:
                result = json.loads(payload)
                if not isinstance(result, dict | list):
                    raise InvalidBodyStructureError(
                        "JSON payload part of request should be represented in a form of dictionary/array"
                    )
            except ValueError as e:
                raise InvalidBodyStructureError("Could not parse body as JSON object") from e
        else:
            # by default try to interpret as JSON
            result = parse_body_as_json(self.request)

        return result

    @lazy
    def db_session(self) -> SASession | SAAsyncSession:
        return self.request.lamb_db_session_map[self.__default_db__]

    @staticmethod
    def http_method_not_realized(request, *args, **kwargs):
        # print 'Required HTTP method is not realized. Error request path = %s' % request.path_info
        message = f"Backend problem, required HTTP method {request.method} is not exist on processing view class"
        raise NotRealizedMethodError(message)
