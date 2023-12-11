__version__ = "3.1.3"


import logging

from django.apps import AppConfig

# Lamb Framework
from lamb.utils import inject_app_defaults

logger = logging.getLogger(__name__)


class LambAppConfig(AppConfig):
    name = "lamb"
    verbose_name = "Lamb REST framework"

    def ready(self):
        logger.debug(f"<{self.__class__.__name__}>. Lamb framework initialized")
        inject_app_defaults(__name__)
        logger.debug(f"<{self.__class__.__name__}>. Lamb default settings injected")


default_app_config = "lamb.LambAppConfig"
