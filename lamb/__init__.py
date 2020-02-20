# -*- coding: utf-8 -*-
__author__ = 'KoNEW'

__version__ = '2.1.0'


import logging

from django.apps import AppConfig

from lamb.utils import inject_app_defaults


logger = logging.getLogger(__name__)


class LambAppConfig(AppConfig):
    name = 'lamb'
    verbose_name = 'Lamb REST framework'

    def ready(self):
        logger.debug('Lamb framework initialized')
        inject_app_defaults(__name__)
        logger.debug('Lamb default settings injected')


default_app_config = 'lamb.LambAppConfig'
