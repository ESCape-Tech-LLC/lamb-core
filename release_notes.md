# 3.5.15

**Changes:**

- `lamb.types.annotations.postgresql` - `uuid_pk` revert to logic `default=uuid.uuid4` for compatibility with `sentinel` like logic

# 3.5.14

**Features:**
- `lamb.utils.dpath_value` - for `os.environ` supports `_FILE` like lookup for integration with Docker Secrets or similar solutions

```python
import os
from lamb.utils import dpath_value
from lamb.utils.validators import validate_not_empty

result = dpath_value(os.environ, 'SOME_KEY', str, transform=validate_not_empty)
# in case environment contains SOME_KEY variable - corresponding value would be extracted and validated
# in case SOME_KEY not exist but SOME_KEY_FILE exists - value would be extracted from file and validated
```

# 3.5.13

**Fixes:**

- `lamb.services.aws.s3.S3BucketConfig` - `__str__` and `__repr__` use masked form of dict

# 3.5.12

**Features:**

- `lamb.management.base.LambCommandMixin`
  - now supports async database connections with `--db-async` flag
  - database key argument renamed to `-D/--db-key`

# 3.5.11

**Features:**

- `lamb.json.encoder.JsonEncoder` now supports dataclasses out-of-the-box
- `lamb.utils.transformers.transform_typed_list` now supports dataclasses for elements creation if income item is dict

# 3.5.10

**Bug fixes:**

- `lamb.utils.filters.DateFilter` - vary min/max produce date instances

# 3.5.9

**Features:**

- `lamb.utils.a_response_paginated` - initial version of agnostic paginator

# 3.5.8

**Features**
- `lamb.filters.DatetimeFilter` - bug fixed to act as datetime transformer, default format changed to `iso`
- `lamb.filters.DateFilter` - actual date filter
- `lamb.utils.response_sorted` - supports sqlalchemy 2 `Select` object with proper typehints
- `lamb.utils.response_filtered` - supports sqlalchemy 2 `Select` object with proper typehints

# 3.5.6

**Features:**
- `lamb.exc.BusinessLogicError` - new exception for actions prohibited from business logic point of view with `error_code=221` and `status_code=400`

**Database processing changed:**

- `LambRequest.lamb_db_session_map` - new field that contains session makers for all known databases (from LAMB_DB_CONFIG settings)
  - `dict[str, sqlalchemy.orm.Session]` in sync mode 
  - `dict[str, sqlalchemy.ext.asyncio.AsyncSession]` in async mode
- `lamb.middleware.db.LambSQLAlchemyMiddleware` modified to act as complex contextmanager with connections to all known databases
- `lamb.rest.RestView` modified in two ways:
  - `__default_db__` - class level dunder variable declaring database default db_key on view (default value is "default" - oO)
  - `db_session` - lazy attribute of view that provides access to db_session with key from `__default_db__`
  
_Example:_
```python
# old style
@a_rest_allowed_http_methods(["GET"])
class SomeView(RestView):
    async def get(self, request: LambRequest):
        async with lamb_db_context(db_key='pythia', pooled=True) as db_session:
            db_session = request.lamb_db_session_map['pythia']
            result = await db_session.execute(select(Area))
            response = result.scalars().all()
            return response

# access db_session from mapping
@a_rest_allowed_http_methods(["GET"])
class SomeView(RestView):
    async def get(self, request: LambRequest):
        db_session = request.lamb_db_session_map['pythia']
        result = await db_session.execute(select(Area))
        response = result.scalars().all()
        return response
    
# access db_session by default on view
class PythiaView(RestView):
    __default_db__ = 'pythia'
    
@a_rest_allowed_http_methods(["GET"])
class SomeView(PythiaView):
    async def get(self, request: LambRequest):
        result = await self.db_session.execute(select(Area))
        response = result.scalars().all()
        return response
```


# 3.5.3

**Features:**

- `lamb.contrib.handbook` - new base module for handbooks and enum based handbooks
- `lamb.db.dialects.postgres` - new module mixing postgresql ENUMs with enum based handbooks
- `lamb.db.session` - declarative bases and corresponding metadata stored in registry to reuse in models creation and subclassing
- `lamb.json` - mixin and encoder adapted to support generic `ResponseConformProtocol`
- `lamb.management.base` - accept target database key as argument
- `lamb.management.commands.alchemy_create` - accept target database argument to work over required metadata
- `lamb.management.csv_command` - base CSV command command
- `lamb.types.intrstrenum_type` - database representation of paired int/str handbook
- `lamb.utils.core.class_or_instance_method` - new descriptor
- `lamb.exc.ProgrammingError` - new exception for with `error_code=17` and `status_code=500`

# 3.5.0

**Dependencies:**
- `psycogp2` bumped to actual version
- `uvicorn-worker` included within ASGI pack

**Features:**

- `RequestRangeError` new error with `status_code=416` and `error_code=16` for requests where requested data range invalid for object
- `lamb.utils.get_settings_value` discover usage of old styled configs and raise warnings (actually would use default lamb value)
- `lamb.utils.humanize_bytes` bytes in human friendly form
- `lamb.utils.bank_card_type_parse` bank card issuer parsing based on masked card number
- `lamb.types.*` moved to files with `_type.py` suffix 
- `lamb.types.dataclasses.bytes_range` contains `BytesRange` class suitable to parse `Range` header and calculate corresponding length and ranges data
- `lamb.db.inspect` moved to `lamb.db.reflect`
- `lamb.db.logging` moved to `lamb.db.log`
- JSON logging formatters changed:
  - camelCased fields replaced with snake_case variants
  - `level_value` new field contains syslog severity level value
  - `module_name` field remove
  - `file_name` fidl now represents full fila path
  - 

**Middlewares:**

- `LambMiddlewareMixin` replacement for old `AsyncMiddlewareMixin` aimed for modern style middlewares only
- coroutine checking fixed to properly work in ASGI mode under python 3.12+
- CORS, XRay, DeviceInfo, GRequest adpated to new base class
- `LambEventLoggingMiddleware` deprecated and combined with `LambXRayMiddleware`:
  - track_id field deprecated
  - new `xline` field paired to `xray` introduced, by default would have `None` value (omit not explicit tracing)
- `LambSQLAlchemyMiddleware` adapted to new base class and check underlying view (view or middleware) on async mode support - in this case produce AsyncSession object


**Tools:**
- Lint, format tools migrated to `ruff`
- Bump version tool migrated to `bump-my-version`
> NOTE: pre-commit hooks should be reinstalled

**Settings:**
- `LAMB_VERBOSE_SQL_LOG` renamed to `LAMB_LOG_SQL_VERBOSE`
- `LAMB_VERBOSE_SQL_LOG_THRESHOLD` renamed to `LAMB_LOG_SQL_VERBOSE_THRESHOLD`
- `LAMB_LOGGING_HEADER_XRAY` renamed to `LAMB_LOG_HEADER_XRAY`
- `LAMB_LOG_HEADER_XLINE` new config for xline header name
- `LAMB_LOG_LEVEL_SEVERITY` new config for python log levels mapping into syslog severity levels (default acts like `pygelf`)
- `LAMB_ADD_CORS_HEADERS` value change - add `Range`, `X-Lamb-XLine` and drop `X-Lamb-TrackID`

**Deprecations:**
- Old `acquiring` module removed

# 3.4.16

**features**

- `LAMB_RESPONSE_EXCEPTION_SERIALIZER` - new config provide ability to modify exception serialization
- `lamb.utils.default_views` adapted to produce error from middleware classmethod to follow error style  

**Usage**:

```python
import enum
from typing import Tuple, Any
from lamb.exc import ApiError
from collections import OrderedDict

@enum.unique
class AppErrorCodes(enum.IntEnum):
    UserNotExist = 1001
    UserKeyIvEmpty = 1002
    Decryption = 1003
    
    
def lamb_exception_serializer(exc: ApiError) -> Tuple[Any, int]:
    match exc.app_error_code:
        case AppErrorCodes.Decryption:
            exc.app_error_code = 100
            exc.status_code = 401
        case (AppErrorCodes.UserNotExist | AppErrorCodes.UserNotExist):
            exc.app_error_code = 3
            exc.status_code = 401
        case _:
            exc.app_error_code = 0
            exc.status_code = 500

    result = OrderedDict()
    result['errorCode'] = exc.app_error_code
    result['errorMessage'] = exc.message
    return result, exc.status_code

LAMB_RESPONSE_EXCEPTION_SERIALIZER='project_name.settings.lamb_exception_serializer'
```

# 3.4.15

**features**
- `lamb.execution_time.ExecutionTimeMeter.get_log_list` - new method with measures in a form of list of dict (suitable for JSON logs)

# 3.4.14

**fixes**

- s3 `kwargs` compacting before send
- s3 delete supports `kwargs` for low-level api

# 3.4.13

**changes**

- logging `exc_info` field replaced with logstash standard `stack_trace`

# 3.4.12

**changes**

- `lamb.exc.ExternalServiceError`: status code changed from 501 to 502 for better compatibility
- `HEAD` requests in case of exception returns empty body for better compatibility
- S3 wrapper changed:
  - `head_object` method realized to retrieve low-level HEAD response from S3 storage
  - `client` property gives access for low-level client connection (dangerous zone with internal property access, but can be useful in case of specific methods required in project)
  - all underlying requests to S3 API enveloped in try/catch block to emit ExternalServiceError in case of botocore.exceptions.ClientError occurred

# 3.4.11

**features**
- LAMB_EXECUTION_TIME_STORE: new config - boolean indicates to store data in database or not. Can be used to log execution time in log records without database write attempts
- `lamb.middleware.execution_time.LambExecutionTimeMiddleware` final log extra context changed
- `lamb.middleware.execution_time.LambExecutionTimeMiddleware` settings lazy renamed and migrated to default ro version

# 3.4.10

**features**

- `lamb.service.redis.config` - support for async connections with GENERIC/SENTINEL modes

# 3.4.9

**features**

- `lamb.service.redis.cache` - provides decorators for usage with Views (support plain Redis/Valkey nodes and RedisJson/Stack also)

# 3.4.8

**features**
- `lamb.service.image.uploaders.s3.ImageUploadServiceAmazonS3` - migrated to modern `S3BucketConfig` style: accept new arg with connection details or try lookup for `default`
- `lamb.utils.core.masked_string` - new optional string masking utility

# 3.4.7

**features**

- improve JSON logging 
  - `statusCode` assign to log on execution time middleware
  - hide `xray,app_user_id` fields from `extra`, but enable as plain versions
  - hide `extra` if dict is empty
- preparation for rated store on execution_time table

# 3.4.6

**features**
- redis: `lamb.service.redis.config.Config` - renamed `lamb.service.redis.config.RedisConfig`. Old name saved for compatibility - would be removed later
- kafka: base version of kafka config add `lamb.service.kafka.config.KafkaConfig`


# 3.4.5

- fixes on redis configs

# 3.4.4

**features**
- redis: `lamb.service.redis.config.Config` - Redis/Valkey config and utils for support Generic/Sentinel/Cluster versions
- throttling utils moved to `lamb.service.redis.throttling`
- fixed error code on `HumanFriendlyMultipleError`


# 3.4.3

**Features:**
- masking
  - Json logging formatters supports extra field masking. List of hiding keys could be configured with `LAMB_LOG_JSON_EXTRA_MASKING` - default is `['pass', 'password', 'token', 'accessToken']`
  - `lamb.utils.core.masked_dict` now acts as case insensitive mode for string keys
  - _sample_ 
    ```json
    {
      "ts": "2024-07-28T14:07:40.488689",
      "level": "WARNING",
      "pid": 98556,
      "msg": "some message",
      "moduleName": "views",
      "fileName": "views.py",
      "lineNo": 118,
      "extra": {
        "app_user_id": null,
        "xray": "6b292e5b-14a5-44d4-b1f6-69d6e8ebc8b4",
        "pass": "*****",
        "PassWord": "*****"
      },
      "httpMethod": "GET",
      "httpUrl": "/api/ping/",
      "xray": "6b292e5b-14a5-44d4-b1f6-69d6e8ebc8b4",
      "trackId": "94a5c6bf-7230-4e89-b2cc-5824b8f99c0d",
      "elapsedTimeMs": 94.227,
      "urlName": "ping"
    }
    ```

# 3.4.2

**Deprecations:**
- drop old style exceptions: `AuthCredentialsIsNotProvided`, `AuthCredentialsInvalid`, `AuthCredentialsExpired`, `AuthForbidden`

**Features:**
- add predefined gunicorn format strings:
  - `lamb.log.constants.LAMB_LOG_FORMAT_GUNICORN_SIMPLE`
  - `lamb.log.constants.LAMB_LOG_FORMAT_GUNICORN_PREFIXNO`
  - `lamb.log.constants.LAMB_LOG_FORMAT_GUNICORN_VERBOSE`
  - `lamb.log.constants.LAMB_LOG_FORMAT_GUNICORN_VERBOSE_PREFIXNO`
- add default gunicorn logging dict builder: `lamb.log.utils.get_gunicorn_logging_dict`

# 3.4.1

**Dependencies:**
- remove dependency: [lazy](https://pypi.org/project/lazy/)
- remove dependency: [json_log_formatter](https://pypi.org/project/JSON-log-formatter/)

**Features:**

Custom lazy descriptors add:

- `lamb.utils.core.lazy`: acts like drop-in replacement for lazy data-descriptor
- `lamb.utils.core.lazy_ro`: readonly version of lazy descriptor
- `lamb.utils.core.lazy_default`: descriptor that supports default value
- `lamb.utils.core.lazy_default_ro`: read-only version of descriptor with default support

Logging:

- old module version (`lamb.utils.logging`) deprecated and removed
- add new module `lamb.log` with:
  - `lamb.log.utils` - utilities like factory injectors
  - `lamb.log.formatters` - logging formatters
  - `lamb.log.constants` - predefined collection of format strings for log records
- formatters:
  - `lamb.log.formatters._BaseFormatter` - base formatter with `formatTime` method

**Other:**

Default logging configs - would produce ts like `2024-07-11T14:43:48.182546` 
- `LAMB_LOG_FORMAT_TIME_SPEC` = "auto"
- `LAMB_LOG_FORMAT_TIME_SEP` = "T"
- `LAMB_LOG_FORMAT_TIME_ZONE` = None