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