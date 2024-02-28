import logging

# device info
LAMB_DEVICE_INFO_HEADER_FAMILY = "HTTP_X_LAMB_DEVICE_FAMILY"
LAMB_DEVICE_INFO_HEADER_PLATFORM = "HTTP_X_LAMB_DEVICE_PLATFORM"
LAMB_DEVICE_INFO_HEADER_OS_VERSION = "HTTP_X_LAMB_DEVICE_OS_VERSION"
LAMB_DEVICE_INFO_HEADER_LOCALE = "HTTP_X_LAMB_DEVICE_LOCALE"
LAMB_DEVICE_INFO_HEADER_APP_VERSION = "HTTP_X_LAMB_APP_VERSION"
LAMB_DEVICE_INFO_HEADER_APP_BUILD = "HTTP_X_LAMB_APP_BUILD"
LAMB_DEVICE_INFO_HEADER_APP_ID = "HTTP_X_LAMB_APP_ID"
LAMB_DEVICE_INFO_LOCALE_VALID_SEPS = ("_", "-")
LAMB_DEVICE_DEFAULT_LOCALE = "en_US"

LAMB_DEVICE_INFO_CLASS = "lamb.types.device_info.DeviceInfo"
LAMB_DEVICE_INFO_COLLECT_IP = True
LAMB_DEVICE_INFO_COLLECT_GEO = True

# GeoIP2 support (maxmind)
LAMB_GEOIP2_DB_CITY = None
LAMB_GEOIP2_DB_COUNTRY = None
LAMB_GEOIP2_DB_ASN = None

# response/request configs
LAMB_REQUEST_MULTIPART_PAYLOAD_KEY = "payload"

LAMB_PAGINATION_LIMIT_DEFAULT = 100
LAMB_PAGINATION_LIMIT_MAX = 5000
LAMB_PAGINATION_KEY_OFFSET = "offset"
LAMB_PAGINATION_KEY_LIMIT = "limit"
LAMB_PAGINATION_KEY_ITEMS = "items"
LAMB_PAGINATION_KEY_ITEMS_EXTENDED = "items_extended"
LAMB_PAGINATION_KEY_TOTAL = "total_count"
LAMB_PAGINATION_KEY_OMIT_TOTAL = "total_omit"

LAMB_SORTING_KEY = "sorting"

LAMB_RESPONSE_JSON_ENGINE = None
LAMB_RESPONSE_JSON_INDENT = None
LAMB_RESPONSE_DATE_FORMAT = "%Y-%m-%d"
LAMB_RESPONSE_APPLY_TO_APPS = []
LAMB_RESPONSE_ENCODER = "lamb.json.encoder.JsonEncoder"

LAMB_RESPONSE_DATETIME_TRANSFORMER = "lamb.utils.transformers.transform_datetime_seconds_int"

LAMB_ERROR_OVERRIDE_PROCESSOR = None


# image uploading
LAMB_IMAGE_UPLOAD_QUALITY = 87
LAMB_IMAGE_UPLOAD_ENGINE = "lamb.service.image.ImageUploadServiceDisk"


# AWS
LAMB_AWS_ACCESS_KEY = None
LAMB_AWS_SECRET_KEY = None
LAMB_AWS_BUCKET_NAME = None
LAMB_AWS_REGION_NAME = None
LAMB_AWS_BUCKET_URL = None
LAMB_AWS_ENDPOINT_URL = None


# utils
LAMB_EXECUTION_TIME_COLLECT_MARKERS = False
LAMB_EXECUTION_TIME_LOG_TOTAL_LEVEL = logging.INFO
LAMB_EXECUTION_TIME_SKIP_METHODS = "OPTIONS"
LAMB_EXECUTION_TIME_TIMESCALE = False
LAMB_EXECUTION_TIME_TIMESCALE_CHUNK_INTERVAL = "7 days"  # in seconds or explicit value
LAMB_EXECUTION_TIME_TIMESCALE_RETENTION_INTERVAL = "180 days"  # Optional, in seconds or explicit value
LAMB_EXECUTION_TIME_TIMESCALE_COMPRESS_AFTER = "60 days"  # Optional, in seconds or explicit value

LAMB_VERBOSE_SQL_LOG = False
LAMB_VERBOSE_SQL_LOG_THRESHOLD = None

LAMB_DPATH_DICT_ENGINE = "dpath"

# logging
LAMB_LOG_LINES_FORMAT = "DEFAULT"
LAMB_LOGGING_HEADER_XRAY = "HTTP_X_LAMB_XRAY"


# services
LAMB_REDIS_URL = "redis://localhost:6379/0"

LAMB_BROKER_URL = "amqp://guest:guest@localhost:5672//"
LAMB_BROKER_RESULT_URL = "redis://localhost:6379/1"

LAMB_CARD_TYPE_PARSER = "lamb.acquiring.rbs._default_card_type_parser"

# database default configs
DB_PORT = None
DB_SESSION_OPTS = None

# pools usage on technical services
LAMB_DB_CONTEXT_POOLED_METRICS = False
LAMB_DB_CONTEXT_POOLED_SETTINGS = False


# CORS support for local tests
LAMB_ADD_CORS_ENABLED = False
LAMB_ADD_CORS_ORIGIN = "*"
LAMB_ADD_CORS_METHODS = "GET,POST,OPTIONS,DELETE,PATCH,COPY"
LAMB_ADD_CORS_CREDENTIALS = "true"
LAMB_ADD_CORS_HEADERS = [
    "User-Agent",
    "Keep-Alive",
    "Content-Type",
    "Origin",
    "Referer",
    "Content-Length",
    "Connection",
    "Accept-Encoding",
    "Accept",
    "If-Modified-Since",
    "Cache-Control",
    "X-Requested-With",
    "X-Lamb-Auth-Token",
    "X-Lamb-Device-Family",
    "X-Lamb-Device-Platform",
    "X-Lamb-Device-OS-Version",
    "X-Lamb-Device-Locale",
    "X-Lamb-App-Version",
    "X-Lamb-App-Build",
    "X-Lamb-XRay",
    "X-Lamb-TrackID",
]
