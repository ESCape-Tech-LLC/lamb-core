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