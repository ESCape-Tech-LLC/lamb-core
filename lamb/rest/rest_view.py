__author__ = 'KoNEW'
#-*- coding: utf-8 -*-

from functools import update_wrapper
from django.utils.decorators import classonlymethod
from lamb.rest.exceptions import NotRealizedMethodError


class RestView(object):
    """ Abstract class for dispatching url requests in REST logic

    Class works in a similar way to django class based views to dispatch http methods.
    """

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

    @staticmethod
    def http_method_not_realized(request, *args, **kwargs):
        # print 'Required HTTP method is not realized. Error request path = %s' % request.path_info
        message = 'Backend problem, required HTTP method %s is not exist on processing view class' % request.method
        raise NotRealizedMethodError(message)
