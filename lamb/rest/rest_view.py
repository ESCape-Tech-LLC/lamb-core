#-*- coding: utf-8 -*-
__author__ = 'KoNEW'


import six
import logging
import json
import xmltodict

from functools import update_wrapper
from lazy import lazy
from django.utils.decorators import classonlymethod
from django.http import HttpRequest

from lamb.exc import NotRealizedMethodError, InvalidBodyStructureError
from lamb.utils import get_request_body_encoding, parse_body_as_json, CONTENT_ENCODING_JSON, CONTENT_ENCODING_XML, \
    CONTENT_ENCODING_MULTIPART, dpath_value, get_request_accept_encoding

logger = logging.getLogger(__name__)

__all__ = [
    'RestView'
]


class RestView(object):
    """ Abstract class for dispatching url requests in REST logic

    Class works in a similar way to django class based views to dispatch http methods.

    Attributes:
        request (HttpRequest): Http request of view
    """

    def __init__(self, **kwargs):
        """
        Constructor. Called in the URLconf; can contain helpful extra
        keyword arguments, and other things.
        """
        # assign for proper type hints
        self.request = None

        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    @classonlymethod
    def as_request_callable(cls):
        """ Main entry point for a request-response process. """
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
    def parsed_body(self) -> dict:
        content_type = self.request_content_type
        logger.debug('Request body encoding discovered: %s' % content_type)

        if content_type == CONTENT_ENCODING_XML:
            try:
                result = xmltodict.parse(self.request.body)
                result = result['request']
            except Exception as e:
                logger.error('XML body parsing failed: %s. RAW: %s' % (e, self.request.body))
                raise InvalidBodyStructureError('Could not parse body as XML tree') from e
        elif content_type == CONTENT_ENCODING_MULTIPART:
            payload = dpath_value(self.request.POST, 'payload', str)
            try:
                result = json.loads(payload)
                if not isinstance(result, dict):
                    raise InvalidBodyStructureError(
                        'JSON payload part of request should be represented in a form of dictionary')
            except ValueError as e:
                raise InvalidBodyStructureError('Could not parse body as JSON object')
        else:
            # by default try to interpret as JSON
            result = parse_body_as_json(self.request)

        return result


    @staticmethod
    def http_method_not_realized(request, *args, **kwargs):
        # print 'Required HTTP method is not realized. Error request path = %s' % request.path_info
        message = 'Backend problem, required HTTP method %s is not exist on processing view class' % request.method
        raise NotRealizedMethodError(message)
