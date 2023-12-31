# 2.4.9
**Features:**
* Added logs lines formatting support via `LAMB_LOG_LINES_FORMAT` config (`PREFIX` added info before each line, `SINGLE_LINE` concatenates strings into one, `DEFAULT` - for default)
  * NB: Don't forget set LOGGING.formatters.\<name>.class as `lamb.types.logging.LambFormatter`

# 2.4.8
**Features:**
* Added support <=, >=, <, > for JsonDataFilter

# 2.4.7
**Features:**
* Added support for various separators for Device Locale - `LAMB_DEVICE_INFO_LOCALE_VALID_SEPS` at config (`'_', '-'`, by default)

**Fixes**
* Device Locale parse error does not affect on other DeviceInfo attributes


# 2.4.6:

**Features:**
* Add support for CORS middleware out of box - useful for localhost debug purpose. Add `lamb.rest.middleware.LambCorsMiddleware` in middleware list and change configs to use

* Configs:
  - NEW: `LAMB_ADD_CORS_ENABLED = False` - basic boolean flag to add/skip CORS headers in reponse
  - NEW: `LAMB_ADD_CORS_ORIGIN = '*'` - allowed origins
  - NEW: `LAMB_ADD_CORS_METHODS = 'GET,POST,OPTIONS,DELETE,PATCH'` - allowed HTTP methods 
  - NEW: `LAMB_ADD_CORS_CREDENTIALS = 'true'` - allowed credentials 
  - NEW: `LAMB_ADD_CORS_HEADERS = ['User-Agent', 'Keep-Alive', 'Content-Type', 'Origin', 'Referer', 'Content-Length', 'Connection', 'Accept-Encoding', 'Accept', 'If-Modified-Since', 'Cache-Control', 'X-Requested-With', 'X-Lamb-Auth-Token', 'X-Lamb-Device-Family', 'X-Lamb-Device-Platform', 'X-Lamb-Device-OS-Version', 'X-Lamb-Device-Locale', 'X-Lamb-App-Version', 'X-Lamb-App-Build']` - allowed headers


# 2.4.5:

**Features:**

* Device's info collection scheme changed
  - New methods `get_device_info_class` and `device_info_factory` act like abstract construction pipeline
  - `DeviceInfoMiddleware` adapted to act based on dynamic device info class
  - `DeviceInfo` collects new fields: `ip_address, ip_routable, geoip2_info`

* Images:
  - deep refactoring
  - add support for images list slices data type

* Configs:
  - NEW: `LAMB_DEVICE_INFO_CLASS = 'lamb.types.device_info.DeviceInfo'`  can be used to specify project specific version of device info class to be used within middleware processing. Project based subclass of `DeviceInfo` should implement `parse_request` method to provide additional dataclass fields
  - NEW: `LAMB_DEVICE_INFO_COLLECT_IP = True` can be used to turn on/off ip info collection
  - NEW: `LAMB_DEVICE_INFO_COLLECT_GEO = True` can be used to turn on/off GeoIP2 info collection
  - NEW: `LAMB_GEOIP2_DB_CITY = None, LAMB_GEOIP2_DB_COUNTRY = None, LAMB_GEOIP2_DB_ASN = None` should be used to specify GeoIP2 databases paths 

# 2.4.4:

* `celery` dependency compatible version increased up to 4.4.7
  
# 2.4.3:

**Fixes:**

* `orjson` response encoding fixed - probably would be used as default json engine in future 
 

# 2.1.0:

**Configs:**

* `LAMB_REDIS_URL` - in-memory storage, also used as async broker result backend (default `'redis://localhost:6379/0'`)
* `LAMB_BROKER_URL` - async message broker (default `'amqp://guest:guest@localhost:5672//'`)
* `LAMB_BROKER_RESULT_URL` - async message broker result backend (default `'redis://localhost:6379/1'`)
* `LAMB_ERROR_OVERRIDE_PROCESSOR` - error construction override method, should be callable object accepting exception as param and modify it in place or returning new exception instance (default `None`). 

**Exceptions:**

* Constructor refactoring - all LambCore exception has been refactored:
  - `__init__` method has been deprecated, use class level variables `_app_error_code`,`_status_code`, `_message` instead
  - `__repr__` method has been add for debug purpose
* New exceptions:
  -  `ThrottlingError` - used for rate-limited resource access in case of rule violation (error_code=101, http_status=429)
  -  `UpdateRequiredError` - used for control device app versions (error_code=201, http_status=400)
  -  `DatabaseError` - database error wrapper (error_code=12, http_status=500)
  -  `HumanFriendlyError` - special case for errors that can be presented to user AS-IS (error_code=202, http_status=400)
  -  `HumanFriendlyMultipleError` - special case for wrapping several user friendly errors (error_code=203, http_status=400)

* Exception handling in REST middleware
  -  all exceptions now wraps in `ApiError` instance before json response encoding
  -  after wrapping all exceptions processed with `LAMB_ERROR_OVERRIDE_PROCESSOR` if it is not None
  -  in case of wrapping callable invalid or failed - all errors wraps in `ImproperlyConfiguredError` object

*Sample*  

```python
# in settings.py or config.py declare
LAMB_ERROR_OVERRIDE_PROCESSOR = 'api.exc.exception_processor'

# in api.exc add function
def exception_processor(exc: ApiError) -> ApiError:
    if isinstance(exc, UpdateRequiredError):
        exc.app_error_code = -1
        exc.status_code = 502
        exc.message = 'Application update required'
        
    return exc
```

**Throttling:**

* `lamb.service.throttling` module add support for 2 methods:
	- `redis_rate_check_pipelined` - simple pipeline rate-limiter working in Counter style, can be used on fast and rare requests, disadvantage is garbage overhead collecting due repeated requests
	- `redis_rate_check_lua` - advanced rate-limiter also working in style of time based Counter, but communicate with Redis backend in signle request mode and prechecking incremental Counter

**Other:**

* Deprecation class 
 - `lamb.utils.DeprecationClassHelper` - class wrapper to mark deprecated classes, can be used as

```python
# old version
class UpdateRequiredError(ClientError):
    """ Error for forced client update required"""
    _app_error_code = VMessengerErrorCodes.UpdateRequired
    _status_code = 400
    _message = None
    

# migrated version
from lamb.utils import DeprecationClassHelper
from lamb.exc import UpdateRequiredError as LambUpdateRequiredError

UpdateRequiredError = DeprecationClassHelper(LambUpdateRequiredError)
```

* Version checking
 - `lamb.utils.check_device_info_min_versions` - utility function for check request against minimal version of application supported by server

```python
min_versions = [('ios', 100), ('android', 100)]
check_device_info_min_versions(request, min_versions)
```

