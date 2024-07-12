# 3.4.0

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
  - 

**Other:**

Default logging configs - would produce ts like `2024-07-11T14:43:48.182546` 
- `LAMB_LOG_FORMAT_TIME_SPEC` = "auto"
- `LAMB_LOG_FORMAT_TIME_SEP` = "T"
- `LAMB_LOG_FORMAT_TIME_ZONE` = None