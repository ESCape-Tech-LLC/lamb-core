import logging

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LAMB_APP_NAME: str | None = Field(None)

    # device info
    LAMB_DEVICE_INFO_HEADER_FAMILY: str = Field("HTTP_X_LAMB_DEVICE_FAMILY")
    LAMB_DEVICE_INFO_HEADER_PLATFORM: str = Field("HTTP_X_LAMB_DEVICE_PLATFORM")
    LAMB_DEVICE_INFO_HEADER_OS_VERSION: str = Field("HTTP_X_LAMB_DEVICE_OS_VERSION")
    LAMB_DEVICE_INFO_HEADER_LOCALE: str = Field("HTTP_X_LAMB_DEVICE_LOCALE")
    LAMB_DEVICE_INFO_HEADER_APP_VERSION: str = Field("HTTP_X_LAMB_APP_VERSION")
    LAMB_DEVICE_INFO_HEADER_APP_BUILD: str = Field("HTTP_X_LAMB_APP_BUILD")
    LAMB_DEVICE_INFO_HEADER_APP_ID: str = Field("HTTP_X_LAMB_APP_ID")
    LAMB_DEVICE_INFO_LOCALE_VALID_SEPS: tuple[str] = Field(("_", "-"))
    LAMB_DEVICE_DEFAULT_LOCALE: str = Field("en_US")

    LAMB_DEVICE_INFO_CLASS: str = Field("lamb.types.device_info_type.DeviceInfo")
    LAMB_DEVICE_INFO_COLLECT_IP: bool = Field(True)
    LAMB_DEVICE_INFO_COLLECT_GEO: bool = Field(True)

    # GeoIP2 support (maxmind)
    LAMB_GEOIP2_DB_CITY: str | None = Field(None)
    LAMB_GEOIP2_DB_COUNTRY: str | None = Field(None)
    LAMB_GEOIP2_DB_ASN: str | None = Field(None)

    # response/request configs
    LAMB_REQUEST_MULTIPART_PAYLOAD_KEY: str = Field("payload")

    LAMB_PAGINATION_LIMIT_DEFAULT: int = Field(100, gt=0)
    LAMB_PAGINATION_LIMIT_MAX: int = Field(5000, gt=0)
    LAMB_PAGINATION_KEY_OFFSET: str = Field("offset")
    LAMB_PAGINATION_KEY_LIMIT: str = Field("limit")
    LAMB_PAGINATION_KEY_ITEMS: str = Field("items")
    LAMB_PAGINATION_KEY_ITEMS_EXTENDED: str = Field("items_extended")
    LAMB_PAGINATION_KEY_TOTAL: str = Field("total_count")
    LAMB_PAGINATION_KEY_OMIT_TOTAL: str = Field("total_omit")

    LAMB_SORTING_KEY: str = Field("sorting")

    LAMB_RESPONSE_JSON_ENGINE: str | None = Field(None)
    LAMB_RESPONSE_JSON_INDENT: str | None = Field(None)
    LAMB_RESPONSE_DATE_FORMAT: str = Field("%Y-%m-%d")
    LAMB_RESPONSE_APPLY_TO_APPS: list | None = Field(None)
    LAMB_RESPONSE_ENCODER: str = Field("lamb.json.encoder.JsonEncoder")
    LAMB_RESPONSE_EXCEPTION_SERIALIZER: str | None = Field(None)
    LAMB_RESPONSE_DATETIME_TRANSFORMER: str = Field("lamb.utils.transformers.transform_datetime_seconds_int")

    LAMB_ERROR_OVERRIDE_PROCESSOR: str | None = Field(None)

    # image uploading
    LAMB_IMAGE_UPLOAD_QUALITY: int = Field(87)
    LAMB_IMAGE_UPLOAD_ENGINE: str = Field("lamb.service.image.ImageUploadServiceDisk")

    # AWS
    LAMB_AWS_ACCESS_KEY: str | None = Field(None)
    LAMB_AWS_SECRET_KEY: str | None = Field(None)
    LAMB_AWS_BUCKET_NAME: str | None = Field(None)
    LAMB_AWS_REGION_NAME: str | None = Field(None)
    LAMB_AWS_BUCKET_URL: str | None = Field(None)
    LAMB_AWS_ENDPOINT_URL: str | None = Field(None)

    # utils
    LAMB_EXECUTION_TIME_COLLECT_MARKERS: bool = Field(False)
    LAMB_EXECUTION_TIME_LOG_TOTAL_LEVEL: int = Field(logging.INFO)
    LAMB_EXECUTION_TIME_STORE_RATES = dict()
    LAMB_EXECUTION_TIME_STORE: bool = Field(True)
    LAMB_EXECUTION_TIME_SKIP_METHODS: str = Field("OPTIONS")
    LAMB_EXECUTION_TIME_TIMESCALE: bool = Field(False)
    LAMB_EXECUTION_TIME_TIMESCALE_CHUNK_INTERVAL: str = Field("7 days")  # in seconds or explicit value
    LAMB_EXECUTION_TIME_TIMESCALE_RETENTION_INTERVAL: str = Field("180 days")  # Optional, in seconds or explicit value
    LAMB_EXECUTION_TIME_TIMESCALE_COMPRESS_AFTER: str = Field("60 day")  # Optional, in seconds or explicit value

    LAMB_DPATH_DICT_ENGINE: str = Field("dpath")

    # logging
    LAMB_LOG_LINES_FORMAT: str = Field("DEFAULT")
    LAMB_LOG_FORMAT_TIME_SPEC: str = Field("auto")
    LAMB_LOG_FORMAT_TIME_SEP: str = Field("T")
    LAMB_LOG_FORMAT_TIME_ZONE: str | None = Field(None)
    LAMB_LOG_JSON_ENABLE: bool = Field(False)
    LAMB_LOG_JSON_HIDE: list | None = Field(None)
    LAMB_LOG_JSON_EXTRA_MASKING = ["pass", "password", "token", "accessToken"]
    LAMB_LOG_HEADER_XRAY: str = Field("HTTP_X_LAMB_XRAY")
    LAMB_LOG_HEADER_XLINE: str = Field("HTTP_X_LAMB_XLINE")
    LAMB_LOG_SQL_VERBOSE: bool = Field(False)
    LAMB_LOG_SQL_VERBOSE_THRESHOLD: str | None = Field(None)
    LAMB_LOG_LEVEL_SEVERITY: dict[int, int] = Field({
        logging.DEBUG: 7,
        logging.INFO: 6,
        logging.WARNING: 4,
        logging.ERROR: 3,
        logging.CRITICAL: 2,
    })

    # services
    LAMB_REDIS_URL: str = Field("redis://localhost:6379/0")

    LAMB_BROKER_URL: str = Field("amqp://guest:guest@localhost:5672//")
    LAMB_BROKER_RESULT_URL: str = Field("redis://localhost:6379/1")

    LAMB_CARD_TYPE_PARSER: str = Field("lamb.acquiring.rbs._default_card_type_parser")

    # database default configs
    DB_PORT: int | None = Field(None)
    DB_SESSION_OPTS = None

    # pools usage on technical services
    LAMB_DB_CONTEXT_POOLED_METRICS: bool = Field(False)
    LAMB_DB_CONTEXT_POOLED_SETTINGS: bool = Field(False)

    # CORS support for local tests
    LAMB_ADD_CORS_ENABLED: bool = Field(False)
    LAMB_ADD_CORS_ORIGIN: str = Field("*")
    LAMB_ADD_CORS_METHODS: str = Field("GET,POST,OPTIONS,DELETE,PATCH,COPY")
    LAMB_ADD_CORS_CREDENTIALS: str = Field("true")
    LAMB_CORS: str = Field(
        "User-Agent,Keep-Alive,Content-Type,Origin,Referer,Content-Length,Content-Disposition,Connection,Accept-Encoding,Accept,Range,If-Modified-Since,Cache-Control,DNT,X-Requested-With,X-Mx-ReqToken,X-Lamb-Auth-Token,X-Lamb-Device-Family,X-Lamb-Device-Platform,X-Lamb-Device-OS-Version,X-Lamb-Device-Locale,X-Lamb-Device-Timezone,X-Lamb-App-Version,X-Lamb-App-Build,X-Lamb-App-Id,X-Lamb-App-Type,X-Lamb-XRay,X-Lamb-XLine")

    @computed_field
    @property
    def LAMB_ADD_CORS_HEADERS(self):
        return self.LAMB_CORS.split(",")

    class Config:
        encoding = "utf-8"


settings = Settings()
