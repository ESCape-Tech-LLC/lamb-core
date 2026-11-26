import os

from lamb.log.formatters import RequestJsonFormatter
from lamb.service.aws.config import S3BucketConfig
from lamb.service.kafka.config import KafkaConfig
from lamb.service.redis.config import Mode, RedisConfig

SECRET_KEY = "fake-key-for-testing"
DEBUG = True
ALLOWED_HOSTS = ["testserver"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INSTALLED_APPS = [
    "lamb.LambAppConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "lamb.db.middleware.SQLAlchemyMiddleware",
    "lamb.rest.middleware.LambRestApiJsonMiddleware",
]

ROOT_URLCONF = "tests.api.urls"

LAMB_RESPONSE_APPLY_TO_APPS = [
    "tests",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "debug": True,
        },
    },
]

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": ":memory:",
#     },
# }
LAMB_DB_CONFIG = {
    # postgresql
    "default": {
        "driver": "postgresql+psycopg",
        "async_driver": "postgresql+psycopg",
        "host": os.environ.get("TEST_DB_HOST", "localhost"),
        "db_name": os.environ.get("TEST_DB_NAME", "lamb_test"),
        "port": os.environ.get("TEST_DB_PORT", "5432"),
        "username": os.environ.get("TEST_DB_USER", "lamb_test"),
        "password": os.environ.get("TEST_DB_PASS", "lamb_test_pass"),
        "connect_options": {"target_session_attrs": "read-write"},
        "aconnect_options": {"target_session_attrs": "read-write"},
    },
    "replica": {
        "driver": "postgresql+psycopg",
        "async_driver": "postgresql+psycopg",
        "host": os.environ.get("TEST_DB_HOST", "localhost"),
        "db_name": os.environ.get("TEST_DB_NAME", "lamb_test"),
        "port": os.environ.get("TEST_DB_PORT", "5432"),
        "username": os.environ.get("TEST_DB_USER", "lamb_test"),
        "password": os.environ.get("TEST_DB_PASS", "lamb_test_pass"),
        "connect_options": {"target_session_attrs": "prefer-standby"},
        "aconnect_options": {"target_session_attrs": "prefer-standby"},
    },
}
LAMB_DB_CONTEXT_POOLED_METRICS = True
LAMB_DB_CONTEXT_POOLED_SETTINGS = True

LAMB_VALKEY_CONFIG = RedisConfig(
    host=os.environ.get("TEST_VALKEY_HOST", "localhost"),
    port=int(os.environ.get("TEST_VALKEY_PORT", "36379")),
    password=os.environ.get("TEST_VALKEY_PASSWORD"),
    default_db=int(os.environ.get("TEST_VALKEY_DB", "0")),
    mode=Mode.GENERIC,
)

LAMB_KAFKA_CONFIG = KafkaConfig(
    bootstrap_servers=os.environ.get("TEST_KAFKA_BOOTSTRAP_SERVERS", "localhost:39092,localhost:39093").split(","),
    security_protocol="PLAINTEXT",
)

LAMB_S3_CONFIG = S3BucketConfig(
    endpoint_url=os.environ.get("TEST_S3_ENDPOINT", "http://localhost:39000"),
    access_key=os.environ.get("TEST_S3_ACCESS_KEY", "minio"),
    secret_key=os.environ.get("TEST_S3_SECRET_KEY", "minio123"),
    region_name=os.environ.get("TEST_S3_REGION", "us-east-1"),
    bucket_name=os.environ.get("TEST_S3_BUCKET", "test-bucket"),
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": RequestJsonFormatter,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "propagate": True, "level": "WARNING"},
        "api": {"handlers": ["console"], "propagate": True, "level": "DEBUG"},
        "lamb": {"handlers": ["console"], "propagate": True, "level": "WARNING"},
        "py.warnings": {"handlers": ["console"], "propagate": True, "level": "WARNING"},
    },
}
