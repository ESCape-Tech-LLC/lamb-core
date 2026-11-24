# Changelog

## [Unreleased]

**Tools:**

- tools: `AGENTS.md` — complete refactor: new rule structure (LMB-{GROUP}{SEVERITY}{NNN}), status model, merged Code Quality section
- tools: `AGENTS.md` — add `.python-version` and dependency categorization rules
- tools: `docker-compose.test.yml` - complete test infrastructure with 6 services (PostgreSQL 18, Valkey 9.1.1, MinIO, Kafka 3.9)
- tools: `docker-compose.test.yml` - PostgreSQL 18 with TimescaleDB on port 35432
- tools: `docker-compose.test.yml` - Valkey bundle 9.1.1 in 3 modes: standalone (36379), Sentinel (36380-36382), Cluster (36390-36392)
- tools: `docker-compose.test.yml` - MinIO S3-compatible storage on ports 39000/39001
- tools: `docker-compose.test.yml` - Kafka 3.9 cluster in KRaft mode (2 nodes, ports 39092-39093)
- tools: `docker-compose.test.yml` - password authentication on all Valkey services (testpass123)
- tools: `docker-compose.test.yml` - health checks for automatic service readiness monitoring
- tools: `scripts/start-test-env.sh` - automated test environment startup with health checks and service initialization
- tools: `scripts/stop-test-env.sh` - clean teardown with volume removal
- tools: `scripts/wait-for-healthy.sh` - reusable Docker service health check script with configurable timeout
- tools: `scripts/sentinel-entrypoint.sh` - dynamic Valkey Sentinel configuration with master IP discovery
- tools: `TESTING.md` - comprehensive testing guide with service configuration and troubleshooting

**Dependencies:**

- dep: merge `test` dependency group into `dev` (pytest-asyncio moved)
- dep: remove `aioredis` from project dependencies - not used in codebase

**Documentation:**

- docs: add `TESTING.md` - testing infrastructure guide with quick start, fixtures reference, and CI/CD example
- docs: consolidate test documentation (removed `tests/README.md`, `scripts/README.md`)
- docs: add MIT LICENSE file

**Chores:**

- chore: update ruff to v0.17.6 in pre-commit hooks
- chore: add PyPI classifiers (Intended Audience, License, Topic, Typing)

---

## [3.7.4] - 2026-11-24

**Tools:**

- tools: `bump.sh` improved and fixed in changelog

---

## [3.7.2] - 2026-11-24

**Dependencies:**

- dep: bump all major dependencies
- tools: bump pre-commit and other tool versions

**Documentation:**

- doc: README.md updated
  - Section 3.1 "Database Configuration": migrated to `LAMB_DB_CONFIG` with SQLAlchemy sync/async drivers
  - Section 3.4: renamed to "Celery Integration"
  - Section 3.5: new "Kafka & Faststream Integration"
  - Section 3.7: new "Recommended ASGI Runners" with Granian recommendation
  - Custom Transformers: updated to use `functools.partial` pattern
  - Cleanup: removed duplicate configuration blocks

---

## [3.7.1] - 2026-09-15

**Features:**

- feat: `lamb.management.commands.lamb_alchemy_create.AsyncLambCommand` - await db_session close on exit

---

## [3.7.0] - 2026-09-15

**Features:**

- feat: `lamb.management.base.AsyncLambCommand` - base async command class
- feat: `lamb.service.aws.utils` - new functions from contrib: `s3_filepath_parse`, `s3_download_file_sync`, `s3_download_file_async`
- feat: `lamb.service.aws.s3engine` - support `str`/`pathlib.Path` objects as key
- feat: `lamb.management.csv_command.CsvCommandMixin` - support RAM effective CSV streaming
- feat: `lamb.management.csv_command.CsvCommandMixin` - support batch streaming
- feat: `lamb.management.csv_command.CsvCommandMixin` - add encoding argument parser

**Breaking Changes:**

- break: `lamb.management.csv_command.CsvCommandMixin` - logic changed to pure mixin, `super().handle()` should be replaced with `self.parse_scv_options()`

**Refactoring:**

- ref: `lamb.service.aws.s3engine` - typing and logging refactoring

**Tools:**

- tools: pre-commit version bump

**Dependencies:**

- dep: bump dependencies
- ref: pyproject linter

---

## [3.6.4] - 2026-09-01

**Features:**

- feat: `lamb.db.middleware` - `LambExecutionTimeMetric` new `exc_info` field (requires table migration)
- feat: `lamb.db.config` - support psycopg3 default connect options
- feat: `lamb.middleware.device_info` - locale parsing with LRU cache
- feat: `lamb.middleware.device_info` - default locale attach moved to DeviceInfo init level
- feat: `lamb.rest.response` - `JsonResponse` add hidden `_lamb_error` attribute
- feat: `lamb.exc` - `ApiError` add `_wrapped_exception` attribute
- feat: `lamb.rest.middleware` - completely rewritten for sync/async compatibility
- feat: `lamb.rest.middleware` - append `Content-Length` header
- feat: `lamb.execution_time.middleware` - completely rewritten for sync/async compatibility
- feat: `lamb.execution_time.middleware` - flush records in background batched task

**Refactoring:**

- ref: `lamb.db.config` - class rename
- ref: `lamb.db.config` - logging improved and fixed
- ref: `lamb.db.context` - logging fixed
- ref: `lamb.middleware.device_info` - adapted for sync/async compatibility
- ref: `lamb.middleware.grequest` - adapted for sync/async compatibility
- ref: `lamb.middleware.xray` - adapted for sync/async compatibility
- ref: `lamb.middleware.abstract` - sync/async middlewares revised
- ref: `lamb.rest.middleware` - logging error info and envelope lines swapped
- ref: `lamb.exc` - `ApiError` repr modified for exception logging

**Deprecations:**

- deprecate: `settings.LAMB_ERROR_OVERRIDE_PROCESSOR` removed
- deprecate: `ExecutionTimeMeter.invalidate()` - use new instance instead

**Chores:**

- chore: `lamb.db.config` - PostgreSQL pool defaults updated for all drivers:
  - `pool_pre_ping=True`
  - `pool_timeout=15`
  - `pool_recycle=1800`
  - `pool_size=10/max_overflow=10` (SYNC)
  - `pool_size=100/max_overflow=100` (ASYNC)

---

## [3.6.3] - 2026-08-21

**Dependencies:**

- dep: add `dotenv`

**Features:**

- feat: rename command `alchemy_create` to `lamb_alchemy_create`
- feat: add new `lamb_env_bust` command

**Refactoring:**

- ref: update pre-commit tools and docs

---

## [3.6.2] - 2026-08-12

**Features:**

- feat: `lamb.db.config` - support psycopg3 default connect options
- feat: `lamb.db.config` - JSON serializer not as lambda for psycopg3 memory leak fix

**Refactoring:**

- ref: `lamb.db.config` - class rename
- ref: logging improved and fixed

**Chores:**

- chore: PostgreSQL pool defaults changed for all drivers and cases:
  - `pool_pre_ping=True`
  - `pool_timeout=15`
  - `pool_recycle=1800`

---

## [3.6.1] - 2026-08-12

**Features:**

- feat: Kafka config normalize protocol/mechanism and provide masked repr

**Refactoring:**

- ref: styling

---

## [3.6.0] - 2026-08-11

**Features:**

- feat: support orjson
- feat: `lamb.log` - log records include logger name in extra

**Dependencies:**

- dep: django version bump

---
