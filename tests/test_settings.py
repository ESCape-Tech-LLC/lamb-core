import logging
import os

ALLOWED_HOSTS = ["testserver"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# collect verbose sqlalchemy log
LAMB_SQLALCHEMY_ECHO = False

SECRET_KEY = "fake-key"
INSTALLED_APPS = ["tests.images", "lamb.LambAppConfig"]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "lamb.middleware.db.LambSQLAlchemyMiddleware",
    "lamb.middleware.rest.LambRestApiJsonMiddleware",
]

ROOT_URLCONF = "tests.api.urls"

LAMB_SQLITE_TEST_DB = "test.db"
LAMB_RESPONSE_APPLY_TO_APPS = [
    "tests",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": "templates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "test_db",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "CONNECT_OPTS": None,
    },
}

LAMB_DB_CONFIG = {
    "default": dict(
        driver="postgresql",
        host="localhost",
        db_name="test_db",
        username="postgres",
        password="postgres",
    )
}

LAMB_STATIC_URL = "/static/"
LAMB_STATIC_FOLDER = os.path.join(BASE_DIR, "static")

LAMB_AWS_ACCESS_KEY = "test"
LAMB_AWS_SECRET_KEY = "test"
LAMB_AWS_BUCKET_NAME = "lamb_images"
LAMB_AWS_BUCKET_ZONE = "s3-ap-southeast-1"

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
LAMB_RESPONSE_ENCODER = "lamb.json.encoder.JsonEncoder"
LAMB_RESPONSE_EXCEPTION_SERIALIZER = None
LAMB_RESPONSE_DATETIME_TRANSFORMER = "lamb.utils.transformers.transform_datetime_seconds_int"

LAMB_ERROR_OVERRIDE_PROCESSOR = None

# image uploading
LAMB_IMAGE_UPLOAD_QUALITY = 87
LAMB_IMAGE_UPLOAD_ENGINE = "lamb.service.image.ImageUploadServiceDisk"


# AWS
LAMB_AWS_REGION_NAME = None
LAMB_AWS_BUCKET_URL = None
LAMB_AWS_ENDPOINT_URL = None


# utils
LAMB_EXECUTION_TIME_COLLECT_MARKERS = False
LAMB_EXECUTION_TIME_LOG_TOTAL_LEVEL = logging.INFO
LAMB_EXECUTION_TIME_STORE_RATES = dict()
LAMB_EXECUTION_TIME_STORE = True
LAMB_EXECUTION_TIME_SKIP_METHODS = "OPTIONS"
LAMB_EXECUTION_TIME_TIMESCALE = False
LAMB_EXECUTION_TIME_TIMESCALE_CHUNK_INTERVAL = "7 days"  # in seconds or explicit value
LAMB_EXECUTION_TIME_TIMESCALE_RETENTION_INTERVAL = "180 days"  # Optional, in seconds or explicit value
LAMB_EXECUTION_TIME_TIMESCALE_COMPRESS_AFTER = "60 days"  # Optional, in seconds or explicit value

LAMB_DPATH_DICT_ENGINE = "dpath"

# logging
LAMB_LOG_LINES_FORMAT = "DEFAULT"
LAMB_LOG_FORMAT_TIME_SPEC = "auto"
LAMB_LOG_FORMAT_TIME_SEP = "T"
LAMB_LOG_FORMAT_TIME_ZONE = None
LAMB_LOG_JSON_ENABLE = False
LAMB_LOG_JSON_HIDE = []
LAMB_LOG_JSON_EXTRA_MASKING = ["pass", "password", "token", "accessToken"]
LAMB_LOG_HEADER_XRAY = "HTTP_X_LAMB_XRAY"
LAMB_LOG_HEADER_XLINE = "HTTP_X_LAMB_XLINE"
LAMB_LOG_SQL_VERBOSE = False
LAMB_LOG_SQL_VERBOSE_THRESHOLD = None
LAMB_LOG_LEVEL_SEVERITY = {  # pygelf inspired
    logging.DEBUG: 7,
    logging.INFO: 6,
    logging.WARNING: 4,
    logging.ERROR: 3,
    logging.CRITICAL: 2,
}

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
# use format from nginx to parse
_CORS = "User-Agent,Keep-Alive,Content-Type,Origin,Referer,Content-Length,Content-Disposition,Connection,Accept-Encoding,Accept,Range,If-Modified-Since,Cache-Control,DNT,X-Requested-With,X-Mx-ReqToken,X-Lamb-Auth-Token,X-Lamb-Device-Family,X-Lamb-Device-Platform,X-Lamb-Device-OS-Version,X-Lamb-Device-Locale,X-Lamb-Device-Timezone,X-Lamb-App-Version,X-Lamb-App-Build,X-Lamb-App-Id,X-Lamb-App-Type,X-Lamb-XRay,X-Lamb-XLine"
LAMB_ADD_CORS_HEADERS = _CORS.split(",")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "propagate": True, "level": "WARNING"},
        "api": {"handlers": ["console"], "propagate": True, "level": "DEBUG"},
        "lamb": {"handlers": ["console"], "propagate": True, "level": "WARNING"},
        "py.warnings": {"handlers": ["console"], "propagate": True, "level": "WARNING"},
    },
}
