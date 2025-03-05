import logging

from django.conf import settings

from lamb.utils import LambRequest


class LoggingDisableMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._previous_level = None

    def __call__(self, request: LambRequest):
        if request.path in settings.LAMB_LOGGING_DISABLED_PATHS:
            try:
                self._previous_level = logging.root.manager.disable
                logging.disable()
                response = self.get_response(request)
            finally:
                logging.disable(self._previous_level)
            return response
        else:
            return self.get_response(request)
