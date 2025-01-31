from functools import wraps

from django.http import HttpResponse

from lamb.exc import NotAllowedMethodError
from lamb.rest.rest_view import RestView

__all__ = ["rest_allowed_http_methods", "a_rest_allowed_http_methods"]


# TODO: combine in one decorator agnostic to sync/async


def rest_allowed_http_methods(method_list):
    def wrapper(wrapped_object):
        @wraps(wrapped_object)
        def inner(request, *args, **kwargs):
            # get method list in proper format
            m_list = [m.upper() for m in method_list]

            # for OPTIONS method return only list of allowed methods
            if request.method == "OPTIONS":
                response = HttpResponse()
                response["Allow"] = ", ".join(m_list)
                response["Content-Length"] = 0
                return response

            # check allowed HTTP methods
            if request.method not in m_list:
                message = "HTTP method {} is not allowed for path={}. Allowed methods ({})".format(
                    request.method,
                    request.path_info,
                    ",".join(m_list),
                )
                raise NotAllowedMethodError(message)

            # try to find callable entry point for request processing
            if issubclass(wrapped_object, RestView):
                return wrapped_object.as_request_callable()(request, *args, **kwargs)
            else:
                return wrapped_object(request, *args, **kwargs)

        return inner

    return wrapper


def a_rest_allowed_http_methods(method_list):
    def wrapper(wrapped_object):
        @wraps(wrapped_object)
        async def inner(request, *args, **kwargs):
            # get method list in proper format
            m_list = [m.upper() for m in method_list]

            # for OPTIONS method return only list of allowed methods
            if (method := request.method) == "OPTIONS":
                response = HttpResponse()
                response["Allow"] = ", ".join(m_list)
                response["Content-Length"] = 0
                return response

            # check allowed HTTP methods
            if method not in m_list:
                allowed_methods = ",".join(m_list)
                message = (
                    f"HTTP method {method} is not allowed for path={request.path_info}. "
                    f"Allowed methods ({allowed_methods})"
                )
                raise NotAllowedMethodError(message)

            # try to find callable entry point for request processing
            if issubclass(wrapped_object, RestView):
                return await wrapped_object.as_request_callable()(request, *args, **kwargs)
            else:
                return wrapped_object(request, *args, **kwargs)

        return inner

    return wrapper
