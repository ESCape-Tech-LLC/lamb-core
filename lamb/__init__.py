__version__ = "3.5.31"


import logging

from django.apps import AppConfig

from lamb.utils import inject_app_defaults, inject_date_format

logger = logging.getLogger(__name__)


class LambAppConfig(AppConfig):
    name = "lamb"
    verbose_name = "Lamb REST framework"

    def ready(self):
        logger.debug(f"<{self.__class__.__name__}>. Lamb framework initialized")
        inject_app_defaults(__name__)
        inject_date_format()
        logger.debug(f"<{self.__class__.__name__}>. Lamb default settings injected")


default_app_config = "lamb.LambAppConfig"
