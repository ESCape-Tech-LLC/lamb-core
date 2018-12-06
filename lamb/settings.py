#-*- coding: utf-8 -*-
__author__ = 'KoNEW'

import warnings

LAMB_DEVICE_INFO_HEADER_FAMILY = 'HTTP_X_LAMB_DEVICE_FAMILY'
LAMB_DEVICE_INFO_HEADER_PLATFORM = 'HTTP_X_LAMB_DEVICE_PLATFORM'
LAMB_DEVICE_INFO_HEADER_OS_VERSION = 'HTTP_X_LAMB_DEVICE_OS_VERSION'
LAMB_DEVICE_INFO_HEADER_LOCALE = 'HTTP_X_LAMB_DEVICE_LOCALE'
LAMB_DEVICE_INFO_HEADER_APP_VERSION = 'HTTP_X_LAMB_APP_VERSION'
LAMB_DEVICE_INFO_HEADER_APP_BUILD = 'HTTP_X_LAMB_APP_BUILD'

LAMB_PAGINATION_LIMIT_DEFAULT = 100
LAMB_PAGINATION_LIMIT_MAX = 5000
LAMB_PAGINATION_KEY_OFFSET = 'offset'
LAMB_PAGINATION_KEY_LIMIT = 'limit'
LAMB_PAGINATION_KEY_ITEMS = 'items'
LAMB_PAGINATION_KEY_ITEMS_EXTENDED = 'items_extended'
LAMB_PAGINATION_KEY_TOTAL = 'total_count'

LAMB_SORTING_KEY = 'sorting'


LAMB_IMAGE_SIZE_THUMBNAIL = 100
LAMB_IMAGE_SIZE_SMALL = 200
LAMB_IMAGE_SIZE_MEDIUM = 400
LAMB_IMAGE_SIZE_LARGE = 800
LAMB_IMAGE_UPLOAD_QUALITY = 87
LAMB_IMAGE_UPLOAD_SERVICE = 'lamb.service.image.ImageUploadServiceDisk'

LAMB_SQLALCHEMY_ECHO = False

LAMB_EXECUTION_TIME_COLLECT_MARKERS = False


LAMB_RESPONSE_JSON_INDENT = None
LAMB_RESPONSE_DATE_FORMAT = '%Y-%m-%d'
LAMB_RESPONSE_OVERRIDE_STATUS_200 = False
LAMB_RESPONSE_APPLY_TO_APPS = []

LAMB_REQUEST_MULTIPART_PAYLOAD_KEY = 'payload'