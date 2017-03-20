__author__ = 'KoNEW'
# -*- coding: utf-8 -*-

from django.http import HttpResponse

from marble.rest.rest_view import RestView
from marble.rest.exceptions import NotAllowedMethodError

def rest_allowed_http_methods(method_list):
    def wrapper(wrapped_object):
        def inner(request, *args, **kwargs):
            # get method list in proper format
            m_list = [ m.upper() for m in method_list ]

            # for OPTIONS method return only list of allowed methods
            if request.method == 'OPTIONS':
                response = HttpResponse()
                response['Allow'] = ', '.join(m_list)
                response['Content-Length'] = 0
                return response

            # check allowed HTTP methods
            if request.method not in m_list:
                message = 'HTTP method %s is not allowed for path=%s. Allowed methods (%s)' % (
                    request.method,
                    request.path_info, ','.join(m_list)
                )
                raise NotAllowedMethodError(message)

            # try to find callable entry point for request processing
            if issubclass(wrapped_object, RestView):
                return wrapped_object.as_request_callable()(request, *args, **kwargs)
            else:
                return wrapped_object(request, *args, **kwargs)
        return inner
    return wrapper
