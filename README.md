# Lamb REST Framework

## 0. Preface

Lamb is a framework layer on top of Django for building JSON-first REST API backends. Lamb **does not replace** Django
entirely, but extends it:

- **Replaces ORM**: SQLAlchemy instead of Django ORM for database access.
- **Adds async-native**: async sessions, Redis, S3, and HTTP clients.
- **JSON-first**: automatic JSON serialization/deserialization, TypedDict schemas, custom error codes.
- **Microservice-ready**: built-in support for X-Ray tracing, Redis caching, S3 storage, pub/sub.

**Lamb does not change** Django routing, middleware infrastructure, or lifecycle. You continue to use `urls.py`,
`Middleware`, `AppConfig` — but with SQLAlchemy, async patterns, and JSON-oriented utilities.

---

## 1. Installation

### Install using `uv`

```bash
uv add git+https://github.com/ESCape-Tech-LLC/lamb-core.git
```

### Install using `pip`

```bash
pip install git+https://github.com/ESCape-Tech-LLC/lamb-core.git
```

or via `requirements.txt`:

```
...
git+https://github.com/ESCape-Tech-LLC/lamb-core.git
...
```

### Install using `poetry`

```bash
poetry add git+https://github.com/ESCape-Tech-LLC/lamb-core.git
```

### Add `lamb` to your project via `settings.py`:

```python
INSTALLED_APPS = [
    "lamb.LambAppConfig",
    "modules.core",
    "modules.main",
    # ... other apps
]

MIDDLEWARE = [
    "lamb.middleware.grequest.LambGRequestMiddleware",
    "lamb.middleware.execution_time.LambExecutionTimeMiddleware",
    "lamb.middleware.device_info.LambDeviceInfoMiddleware",
    "django_asgi_lifespan.middleware.LifespanStateMiddleware",
    "lamb.middleware.xray.LambXRayMiddleware",
    "lamb.middleware.db.LambSQLAlchemyMiddleware",
    "lamb.middleware.rest.LambRestApiJsonMiddleware",
    # ... custom middleware
]
```

---

## 2. Basic Usage

### A. Create API layer module

Create an API module, e.g., `api/` with structure:

```
api/
    urls.py
    views.py
    models.py
    __init__.py
```

Add the module to `INSTALLED_APPS`.

### B. Declare your model in `models.py`

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import VARCHAR, BYTEA, CITEXT, TIMESTAMP
from lamb.db.dialects.postgres import PG_ENUM
from lamb.db.mixins import TimeMarksMixinTZ
from lamb.db.session import DeclarativeBase
from lamb.json.mixins import ResponseEncodableMixin
from lamb.types import DeviceInfoType
from lamb.types.annotations.postgresql import bool_f, bool_t, int_b, int_i, jsonb, str_v, timestamp_tz, uuid_pk
import sqlalchemy as sa
import uuid


# Base model with mixins
class AppBase(TimeMarksMixinTZ, ResponseEncodableMixin, DeclarativeBase):
    __abstract__ = True


# Example User model
class User(AppBase):
    __tablename__ = "app_users"

    # Primary key
    user_id: Mapped[int] = mapped_column(primary_key=True)
    user_uuid: Mapped[uuid.UUID] = mapped_column(sa.UUID)

    # Timestamps
    time_profile_update: Mapped[timestamp_tz] = mapped_column(TIMESTAMP(timezone=True, precision=3))
    time_last_active: Mapped[timestamp_tz | None]

    # Profile fields
    name: Mapped[str_v | None] = mapped_column(VARCHAR(255))
    avatar_url: Mapped[str_v | None] = mapped_column(VARCHAR(2048))

    # Platform enum
    platform: Mapped["Platform"] = mapped_column(PG_ENUM("Platform", name="t_platform"))

    # Device info (JSONB)
    device_info: Mapped[jsonb | None] = mapped_column(DeviceInfoType, server_default=sa.text("NULL"))

    # Context (JSONB for arbitrary data)
    context: Mapped[jsonb | None]

    # Flags
    removed: Mapped[bool_f | None] = mapped_column()
```

**Key points:**

- Use `DeclarativeBase` from `lamb.db.session`
- Mix in `TimeMarksMixinTZ` for automatic `time_created`/`time_updated` timestamps
- Use `ResponseEncodableMixin` for JSON serialization
- Use PostgreSQL-specific types from `lamb.types.annotations.postgresql`
- Use `DeviceInfoType` for device information storage (JSONB)

#### TimeMarksMixinTZ Example

```python
from lamb.db.mixins import TimeMarksMixinTZ
from lamb.db.session import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.dialects.postgresql import TIMESTAMP


class AppBase(TimeMarksMixinTZ, DeclarativeBase):
    __abstract__ = True


class Product(AppBase):
    __tablename__ = "app_product"
    # Automatically has:
    # - time_created: TIMESTAMP WITH TIME ZONE (auto-set on insert)
    # - time_updated: TIMESTAMP WITH TIME ZONE (auto-update on modify)
```

### C. Create database and declare connection

```sql
-- PostgreSQL: Create user and database

-- Drop existing (if needed)
DROP DATABASE IF EXISTS books WITH (FORCE);
DROP USER IF EXISTS books_user;

-- Create user
CREATE USER books_user WITH PASSWORD 'vR0Q9UxKRqPFZpB';

-- Create database
CREATE DATABASE books OWNER books_user ENCODING 'UTF8';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE books TO books_user;
\c books
GRANT ALL PRIVILEGES ON SCHEMA public TO books_user;
```

```python
# settings.py
# Note: Django DATABASES is typically configured with an in-memory SQLite for compatibility,
# but Lamb uses SQLAlchemy directly via lamb_db_configs. The Django DATABASES setting is
# essentially unused in practice for data operations.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # In-memory SQLite - not actually used
    }
}

# Real database configuration for Lamb/SQLAlchemy
LAMB_DB_CONFIGS = {
    "default": {
        "url": "postgresql://user:pass@localhost:5432/mydb",
        # Or use environment variable
        # "url": os.environ["DATABASE_URL"],
    }
}
```

### D. Create your REST views

```python
from lamb.rest.views import RestView
from lamb.rest.decorators import a_rest_allowed_http_methods
from lamb.json import JsonResponse
from lamb.utils import parse_body_as_json, dpath_value
from sqlalchemy import select


@a_rest_allowed_http_methods(["GET", "POST", "PATCH", "DELETE"])
class BookView(RestView):
    async def _find_book(self, request, book_id):
        db_session = request.lamb_db_session
        result = await db_session.execute(select(Book).where(Book.book_id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            from lamb.exc import NotExistError

            raise NotExistError(f"Book {book_id} not found")
        return book

    async def get(self, request, book_id):
        book = await self._find_book(request, book_id)
        return book  # JsonResponse with auto-serialization

    async def post(self, request):
        json_body = parse_body_as_json(request)
        book = Book(
            title=dpath_value(json_body, "title", str),
            isbn=dpath_value(json_body, "isbn", str),
        )
        await request.lamb_db_session.add(book)
        await request.lamb_db_session.commit()  # explicit commit required
        return book

    async def patch(self, request, book_id):
        book = await self._find_book(request, book_id)
        json_body = parse_body_as_json(request)
        book.title = dpath_value(json_body, "title", str, default=book.title)
        book.isbn = dpath_value(json_body, "isbn", str, default=book.isbn)

        await request.lamb_db_session.commit()  # explicit commit required
        return book

    async def delete(self, request, book_id):
        book = await self._find_book(request, book_id)
        await request.lamb_db_session.delete(book)
        await request.lamb_db_session.commit()  # explicit commit required
        return JsonResponse(status=204)
```

**Note**: `LambSQLAlchemyMiddleware` injects `request.lamb_db_session`, but **does not auto-commit**. For write
operations, explicit `await db_session.commit()` is required.

### E. Declare URL endpoints

```python
# api/urls.py
from django.urls import path
from api.views import BookView

app_name = "api"

urlpatterns = [
    path("books/", BookView.as_view(), name="book_list"),
    path("books/<uuid:book_id>/", BookView.as_view(), name="book"),
]
```

---

## 3. Services & Configurations

### 3.1. Database Configuration (LAMB_DB_CONFIG)

Lamb uses `LAMB_DB_CONFIG` for SQLAlchemy database configurations. Supports multiple databases (`default`, `replica`,
`stats`, etc.) with sync/async drivers and connection pooling.

```python
# settings.py
from functools import partial
import os

from lamb.service.redis.config import RedisConfig, Mode


def _connect_options(cfg, sync: bool, pooled: bool, target_session_attrs: str | None = None):
    """Configure connection options based on session type."""
    if cfg.get("multi_host") and target_session_attrs is not None:
        return {"target_session_attrs": target_session_attrs}
    return {}


LAMB_DB_CONFIG = {
    # Primary database (read-write)
    "default": {
        "driver": "postgresql+psycopg",  # Sync driver
        "async_driver": "postgresql+psycopg",  # Async driver
        "host": os.getenv("DB_HOST", "localhost"),  # Can be comma-separated for multi-host
        "port": os.getenv("DB_PORT", "5432"),  # Can be comma-separated
        "db_name": os.getenv("DB_NAME", "app_db"),
        "username": os.getenv("DB_USER", "app_user"),
        "password": os.getenv("DB_PASSWORD", ""),
        "connect_options": partial(_connect_options, target_session_attrs="read-write"),
        "aconnect_options": partial(_connect_options, target_session_attrs="read-write"),
    },
    # Replica database (read-only)
    "replica": {
        "driver": "postgresql+psycopg",
        "async_driver": "postgresql+psycopg",
        "host": os.getenv("DB_REPLICA_HOST", os.getenv("DB_HOST")),
        "port": os.getenv("DB_REPLICA_PORT", os.getenv("DB_PORT")),
        "db_name": os.getenv("DB_NAME"),
        "username": os.getenv("DB_REPLICA_USER", os.getenv("DB_USER")),
        "password": os.getenv("DB_REPLICA_PASSWORD", os.getenv("DB_PASSWORD")),
        "connect_options": partial(_connect_options, target_session_attrs="prefer-standby"),
        "aconnect_options": partial(_connect_options, target_session_attrs="prefer-standby"),
    },
}

# Optional: Enable connection pooling metrics
LAMB_DB_CONTEXT_POOLED_METRICS = True
LAMB_DB_CONTEXT_POOLED_SETTINGS = True
```

#### Multi-host Support (PostgreSQL Replication/Failover)

For multi-host support, use comma-separated hosts and ports:

```python
LAMB_DB_CONFIG = {
    "default": {
        "driver": "postgresql+psycopg",
        "async_driver": "postgresql+psycopg",
        "host": "master.local,replica1.local,replica2.local",  # comma-separated
        "port": "5432,5432,5432",  # comma-separated, aligned with hosts
        "db_name": "app_db",
        "username": "app_user",
        "password": "secure_password",
    }
}
```

> **Note**: This enables automatic failover and read/write splitting for PostgreSQL replication setups.

### 3.2. Redis Configuration

#### Mixed Configuration (Multiple Redis Instances)

Lamb supports configuring multiple Redis instances for different purposes (cache, broker, throttling, etc.):

```python
# settings.py
from lamb.service.redis.config import RedisConfig, Mode

LAMB_REDIS_CONFIG = {
    # Cache - Generic standalone Redis
    "cache": RedisConfig(
        host="redis.local",
        port=6379,
        mode=Mode.GENERIC,
        username=None,
        password="cache_pass",
        default_db=0,
    ),
    # Broker - Redis Sentinel for high availability
    "broker": RedisConfig(
        host="sentinel1,sentinel2,sentinel3",
        port=26379,
        mode=Mode.SENTINEL,
        password="sentinel_pass",
        sentinel_service_name="mymaster",
        default_db=1,
    ),
    # Throttling - Redis Cluster for distributed rate limiting
    "throttling": RedisConfig(
        host="node1,node2,node3",
        port=[6379, 6379, 6379],
        mode=Mode.CLUSTER_101,
        username=None,
        password="cluster_pass",
    ),
    # Session - Another standalone instance for sessions
    "session": RedisConfig(
        host="session-redis.local",
        port=6379,
        mode=Mode.GENERIC,
        password="session_pass",
        default_db=2,
    ),
}
```

#### Usage

```python
from lamb.service.redis.config import LAMB_REDIS_CONFIG

# Generic (cache)
redis_client = LAMB_REDIS_CONFIG["cache"].redis()
redis_client.set("cache_key", 100)
value = redis_client.get("cache_key")

# Sentinel (broker)
redis_master = LAMB_REDIS_CONFIG["broker"].redis()
redis_master.set("broker_key", 100)

# Sentinel slave
redis_slave = LAMB_REDIS_CONFIG["broker"].redis(sentinel_slave=True)
value = redis_slave.get("broker_key")

# Cluster (throttling)
redis_cluster = LAMB_REDIS_CONFIG["throttling"].redis()
redis_cluster.set("throttle_key", 1000)

# Async (generic)
redis_async = await LAMB_REDIS_CONFIG["cache"].aredis()
await redis_async.set("async_key", "value")
```

#### SSL/TLS Options

For SSL connections, use URL format with `rediss` scheme:

```python
LAMB_REDIS_CONFIG = {
    "cache_ssl": RedisConfig(
        host="redis-ssl.example.com",
        port=6380,
        mode=Mode.GENERIC,
        password="secure_password",
        default_db=0,
        # SSL options are passed via URL
        # URL will be: rediss://redis-ssl.example.com:6380/0
    ),
}
```

---

### 3.3. S3 Configuration (MinIO / Custom S3)

#### AWS S3 with Custom Endpoint

```python
# settings.py
from lamb.service.aws.config import S3BucketConfig

LAMB_S3_CONFIG = {
    # Default AWS S3 bucket
    "aws_default": S3BucketConfig(
        bucket_name="my-app-bucket",
        region_name="us-east-1",
        access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        endpoint_url=None,  # AWS default endpoint
        bucket_url="https://my-app-bucket.s3.amazonaws.com",
    ),
    # MinIO / Custom S3 bucket
    "media_minio": S3BucketConfig(
        bucket_name="media",
        region_name="us-east-1",
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        endpoint_url="http://minio.local:9000",  # Custom endpoint
        bucket_url="http://minio.local:9000/media",  # Public URL for file access
        signature_host="http://minio.local:9000",  # Override signature host for pre-signed URLs
    ),
    # DigitalOcean Spaces example
    "do_spaces": S3BucketConfig(
        bucket_name="my-app-media",
        region_name="nyc3",
        access_key=os.getenv("DO_SPACES_KEY"),
        secret_key=os.getenv("DO_SPACES_SECRET"),
        endpoint_url="https://nyc3.digitaloceanspaces.com",
        bucket_url="https://my-app-media.nyc3.digitaloceanspaces.com",
    ),
}
```

> **Note on `signature_host`**: For MinIO and custom S3 endpoints, `signature_host` overrides the host used when
> generating pre-signed URLs. Without this override, AWS SDK may generate URLs with the default AWS endpoint, which won't
> work for custom S3-compatible storage.

#### Usage in Views

```python
from lamb.service.aws.s3engine import AsyncS3Engine


class MediaUploadView(RestView):
    @a_rest_allowed_http_methods(["POST"])
    async def post(self, request):
        # Access S3 engine from lifespan state
        s3_state = request.state["aioboto3"]["media_minio"]
        s3_engine: AsyncS3Engine = s3_state["s3_engine"]

        # Upload file
        file_obj = request.FILES["file"]
        file_path = f"uploads/{uuid.uuid4()}.jpg"

        await s3_engine.upload_fileobj(
            bucket="media",
            key=file_path,
            body=file_obj,
        )

        return {"file_path": file_path}
```

---

### 3.4. Celery Integration

#### Message Broker & Result Backend Configuration

```python
# settings.py
LAMB_BROKER_URL = "redis://localhost:6379/0"  # Redis as broker
LAMB_BROKER_RESULT_URL = "redis://localhost:6379/1"  # Redis as result backend
LAMB_BROKER_TRANSPORT_OPTIONS = {}  # Optional broker-specific options
LAMB_BROKER_RESULT_TRANSPORT_OPTIONS = {}  # Optional result backend options
```

#### Getting Broker URL from Redis Config

```python
# settings.py
from lamb.service.redis.config import RedisConfig, Mode

LAMB_REDIS_CONFIG = {
    "broker": RedisConfig(
        host="redis.local",
        port=6379,
        mode=Mode.GENERIC,
        password="broker_pass",
        default_db=0,
    ),
    "result": RedisConfig(
        host="redis.local",
        port=6379,
        mode=Mode.GENERIC,
        password="broker_pass",
        default_db=1,
    ),
}

# Use Redis config for Celery
LAMB_BROKER_URL = LAMB_REDIS_CONFIG["broker"].broker_url
LAMB_BROKER_RESULT_URL = LAMB_REDIS_CONFIG["result"].url
```

#### Celery App Configuration

Create `celery_config.py` in your project root:

```python
# celery_config.py
import enum
import os

from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
from django.conf import settings
from kombu import Exchange, Queue

import lamb.log.constants
from lamb.log.formatters import CeleryJsonFormatter, CeleryMultilineFormatter

__all__ = ["CeleryQueues", "celery_app"]

# Django init
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myapp.settings")


# Define queues
@enum.unique
class CeleryQueues(enum.StrEnum):
    default = "default"
    email = "email"
    maintenance = "maintenance"


# Create Celery app
celery_app = Celery(
    main="myapp",
    broker=settings.LAMB_BROKER_URL,
    backend=settings.LAMB_BROKER_RESULT_URL,
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    accept_content=["json"],
    enable_utc=True,
    task_queues=tuple([Queue(q, exchange=Exchange(q), routing_key=q) for q in CeleryQueues.__members__]),
    task_default_queue=CeleryQueues.default,
    task_default_exchange=CeleryQueues.default,
    task_default_routing_key=CeleryQueues.default,
    autodiscover_tasks=lambda: settings.INSTALLED_APPS,
    worker_log_format=lamb.log.constants.LAMB_LOG_FORMAT_CELERY_MAIN_SIMPLE,
    worker_task_log_format=lamb.log.constants.LAMB_LOG_FORMAT_CELERY_TASK_SIMPLE,
    broker_transport_options=settings.LAMB_BROKER_TRANSPORT_OPTIONS,
    result_backend_transport_options=settings.LAMB_BROKER_RESULT_TRANSPORT_OPTIONS,
)

# Celery Beat scheduled tasks
celery_app.conf.beat_schedule = {
    "cleanup-expired-sessions": {
        "task": "modules.auth.tasks.cleanup_expired_sessions_task",
        "schedule": 300.0,  # Every 5 minutes
        "options": {"queue": CeleryQueues.maintenance},
    },
}

# Configure logging formatter
celery_formatter_cls = CeleryJsonFormatter if settings.LAMB_LOG_JSON_ENABLE else CeleryMultilineFormatter


@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.setFormatter(celery_formatter_cls(lamb.log.constants.LAMB_LOG_FORMAT_CELERY_TASK_SIMPLE))


@after_setup_logger.connect
def setup_logger(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.setFormatter(celery_formatter_cls(lamb.log.constants.LAMB_LOG_FORMAT_CELERY_MAIN_SIMPLE))
```

#### Register Celery in Django

```python
# __init__.py
from .celery_config import celery_app  # noqa: F401
```

#### Define Tasks

```python
# modules/auth/tasks.py
from celery import shared_task
from myapp.celery_config import CeleryQueues


@shared_task(queue=CeleryQueues.email)
def send_welcome_email(user_id: str):
    user = User.objects.get(user_id=user_id)
    # Send email logic
    pass


@shared_task(queue=CeleryQueues.maintenance)
def cleanup_expired_sessions_task():
    # Maintenance task logic
    pass
```

#### Running Celery Workers

```bash
# Development
celery -A myapp worker -l info -Q default,email,maintenance

# Production (with concurrency and prefetch)
celery -A myapp worker -l info -Q default,email,maintenance \
  --concurrency=4 --prefetch-multiplier=1

# Celery Beat (for scheduled tasks)
celery -A myapp beat -l info
```

#### FastStream Redis Broker (for pub/sub)

```python
# modules/push/utils.py
from faststream.redis import RedisBroker
from django.conf import settings


def get_broker() -> RedisBroker:
    redis_conf = settings.LAMB_REDIS_CONFIG["broker"]
    broker = RedisBroker(
        redis_conf.url,
        logger=logger,
        max_connections=100,
        health_check_interval=20.0,
        retry_on_timeout=True,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        socket_keepalive=True,
    )
    return broker
```

---

### 3.5. Kafka & Faststream Integration

For event-driven architectures, Lamb supports Kafka as a message broker via Celery or Faststream.

#### Faststream Integration

Faststream is a modern async framework for working with Kafka, RabbitMQ, and other message brokers.

```python
# modules/kafka/faststream_app.py
from faststream import FastStream
from faststream.kafka import KafkaBroker, KafkaMessage
from faststream.security import SASLPlaintain

# Create Kafka broker
broker = KafkaBroker("localhost:9092")

# Create FastStream app
app = FastStream(broker)


@broker.subscriber("user-events")
async def handle_user_event(msg: KafkaMessage):
    """Process user events from Kafka."""
    import json

    data = json.loads(msg)
    user_id = data.get("user_id")
    event_type = data.get("event_type")

    # Process event
    print(f"User {user_id} triggered {event_type}")
```

---

### 3.6. Lifespan Manager (Recommended Pattern)

> **Note**: Lifespan manager is **not part of the framework** — it's a recommended pattern and ready-to-use snippet for
> managing shared resources (S3 clients, aiohttp sessions, Redis brokers) in ASGI applications.

#### Define Lifespan Manager

```python
# modules/core/lifespan_manager.py
import contextlib
import logging
from collections import defaultdict

import aiohttp
from django.conf import settings

from lamb.service.aws.s3engine import AsyncS3Engine

logger = logging.getLogger(__name__)

__all__ = ["lifespan_manager"]


@contextlib.asynccontextmanager
async def lifespan_manager():
    state = defaultdict(dict)

    # Attach: aiohttp session
    connector = aiohttp.TCPConnector(limit=200)
    aiohttp_session = aiohttp.ClientSession(
        connector=connector,
        trust_env=True,
    )
    state["aiohttp"]["session"] = aiohttp_session
    logger.debug(f"lifespan_manager. attached. aiohttp_session={aiohttp_session}")

    # Attach: async S3 clients
    stack = contextlib.AsyncExitStack()
    boto3_contexts = []
    for bucket, conn_cfg in settings.LAMB_S3_CONFIG.items():
        aws_client_creator = AsyncS3Engine.construct_async_creator(conn_cfg)
        aws_client = await stack.enter_async_context(aws_client_creator)
        s3_engine = AsyncS3Engine(config=conn_cfg, client=aws_client)

        s3_record = {
            "conn_cfg": conn_cfg,
            "aws_client": aws_client,
            "s3_engine": s3_engine,
        }
        state["aioboto3"][bucket] = s3_record
        logger.debug(f"lifespan_manager. attached. aioboto3 S3 client: {bucket=}")
        boto3_contexts.append(aws_client)

    # Attach: push broker
    from modules.push.utils import get_broker

    push_broker = get_broker()
    await push_broker.connect()
    logger.debug(f"lifespan_manager. attached. push broker={push_broker}")

    # Yield state to requests
    try:
        yield state
    finally:
        logger.info(f"lifespan_manager. closing contexts")
        await push_broker.stop()
        await aiohttp_session.close()
        for ctx in boto3_contexts:
            await ctx.close()
```

#### Register Lifespan Manager

```python
# modules/core/apps.py
from django.apps import AppConfig
from django_asgi_lifespan.register import register_lifespan_manager

from modules.core.lifespan_manager import lifespan_manager


class CoreAppConfig(AppConfig):
    name = "modules.core"

    def ready(self):
        register_lifespan_manager(context_manager=lifespan_manager)
```

#### Use Lifespan State in Views

```python
@rest_allowed_http_methods(["GET", "POST"])
class MediaView(RestView):
    async def post(self, request):
        # Access S3 engine from lifespan state
        s3_state = request.state["aioboto3"]["media_minio"]
        s3_engine: AsyncS3Engine = s3_state["s3_engine"]

        # Upload file
        file_obj = request.FILES["file"]
        file_path = f"uploads/{uuid.uuid4()}.jpg"
        await s3_engine.upload_fileobj(bucket="media", key=file_path, body=file_obj)

        return {"file_path": file_path}

    async def get(self, request, file_path):
        # Use aiohttp session from lifespan state
        session = request.state["aiohttp"]["session"]

        async with session.get(f"http://minio.local:9000/media/{file_path}") as resp:
            content = await resp.read()
            return JsonResponse(content)
```

---

### 3.7. Recommended ASGI Runners

Lamb is designed for async-native operation and supports multiple ASGI runners. The framework automatically detects the
runner from command-line arguments.

#### Granian (Recommended for Production)

Granian is a high-performance ASGI server written in Rust, optimized for async workloads.

```bash
# Start with Granian
granian modules.main.asgi:application --host 0.0.0.0 --port 8000 --workers 4 

# With reload (development)
granian modules.main.asgi:application --host 0.0.0.0 --port 8000 --reload
```

**Granian advantages:**

- Rust-based, high performance
- Native async support
- Multi-worker and multi-threading
- Low memory footprint
- Hot reload for development

#### Daphne (Django Native)

Daphne is the official Django ASGI server, suitable for Django projects.

```bash
# Start with Daphne
daphne -b 0.0.0.0 -p 8000 modules.main.asgi:application

# With verbosity
daphne -b 0.0.0.0 -p 8000 modules.main.asgi:application -v 2
```

#### Uvicorn

```bash
# Start with Uvicorn
uvicorn modules.main.asgi:application --host 0.0.0.0 --port 8000 --reload

# Production (with gunicorn)
gunicorn modules.main.asgi:application -w 4 -k uvicorn.workers.UvicornWorker
```

#### Runner Detection

Lamb automatically detects the runner from command-line arguments:

```python
# modules/main/settings.py
import sys
import warnings


def get_runner() -> str:
    if any("uvicorn" in arg for arg in sys.argv):
        return "uvicorn"
    elif any("granian" in arg for arg in sys.argv):
        return "granian"
    elif any("daphne" in arg for arg in sys.argv):
        return "daphne"
    else:
        warnings.warn(f"Could not determine runner: {sys.argv=}")
        return "unknown"


LAMB_APP_RUNNER = get_runner()
```

> **Recommendation**: Use **Granian** for production deployments due to its performance and low resource consumption.
> Use **Uvicorn** with `--reload` for development.

---

## 4. Error Codes Reference

### Lamb Error Codes

| Code | Exception                   | HTTP Status | Description                     |
|------|-----------------------------|-------------|---------------------------------|
| 0    | Unknown                     | 500         | Unknown error                   |
| 1    | NotAllowedMethodError       | 405         | HTTP method not allowed         |
| 2    | NotRealizedMethodError      | 501         | Method not implemented          |
| 3    | InvalidBodyStructureError   | 400         | Invalid JSON structure          |
| 4    | InvalidParamValueError      | 400         | Invalid parameter value         |
| 5    | InvalidParamTypeError       | 400         | Invalid parameter type          |
| 6    | AuthTokenNotProvidedError   | 401         | Auth token not provided         |
| 7    | AuthTokenInvalidError       | 401         | Auth token invalid              |
| 8    | AuthTokenExpiredError       | 401         | Auth token expired              |
| 9    | AuthForbiddenError          | 403         | Access forbidden                |
| 10   | NotExistError               | 404         | Object not found                |
| 11   | ExternalServiceError        | 502         | External service error          |
| 12   | DatabaseError               | 500         | Database error                  |
| 13   | AlreadyExistError           | 400         | Object already exists           |
| 14   | RequestBodyTooBigError      | 413         | Request body too large          |
| 15   | AuthCredentialsInvalidError | 401         | Invalid credentials             |
| 16   | RequestRangeError           | 416         | Invalid range request           |
| 17   | ProgrammingError            | 500         | Programming/configuration error |
| 101  | ThrottlingError             | 429         | Rate limit exceeded             |
| 201  | UpdateRequiredError         | 400         | Client update required          |
| 202  | HumanFriendlyError          | 400         | Human-readable error            |
| 203  | HumanFriendlyMultipleError  | 400         | Multiple human-readable errors  |
| 211  | UserBlockedError            | 403         | User account blocked            |
| 221  | BusinessLogicError          | 400         | Business logic violation        |

### Custom Error Serialization

```python
# settings.py
from lamb.exc import HTTPException


# Define custom error codes
class AppErrorCodes:
    INVALID_BODY = 1001
    INVALID_PARAMS = 1002
    NOT_FOUND = 1003
    FORBIDDEN = 1004


# Custom error serializer
def custom_error_serializer(error: HTTPException, request=None) -> dict:
    """Custom error serialization with camelCase and code mapping."""
    # Map legacy codes to HTTP status codes
    code_to_status = {
        AppErrorCodes.INVALID_BODY: 400,
        AppErrorCodes.INVALID_PARAMS: 400,
        AppErrorCodes.NOT_FOUND: 404,
        AppErrorCodes.FORBIDDEN: 403,
    }

    status = code_to_status.get(error.code, 500)

    # Convert to camelCase
    return {
        "errorCode": error.code,
        "errorMessage": error.message,
        "details": error.details,
    }


# Apply serializer
LAMB_RESPONSE_EXCEPTION_SERIALIZER = custom_error_serializer
```

### Example Error Response

```json
{
  "errorCode": 1001,
  "errorMessage": "Invalid request body",
  "details": {
    "field": "email",
    "reason": "invalid_format"
  }
}
```

---

## 5. Validators & Transformers

> **Note**: Validators and transformers are often used together and may be merged into a single module in future
> versions.

### Validators

```python
from lamb.utils.validators import (
    validate_required,
    validate_string,
    validate_int,
    validate_float,
    validate_email,
    validate_uuid,
    ValidationError,
)

# Required field
user_id = validate_required(data.get("user_id"), "user_id")

# String validation
name = validate_string(data.get("name"), min_length=1, max_length=100)

# Integer validation
age = validate_int(data.get("age"), min_value=0, max_value=150)

# Email validation
email = validate_email(data.get("email"))

# UUID validation
session_id = validate_uuid(data.get("session_id"))
```

### Transformers

```python
from lamb.utils.transformers import (
    transform_string_enum,
    transform_boolean,
    transform_uuid,
    transform_datetime_seconds_int,
    transform_datetime_iso_milliseconds_zulu,
    tf_list_int,
    tf_list_string,
)

# Enum transformation
status = transform_string_enum("active", UserStatus)

# Boolean transformation
is_active = transform_boolean("true")  # True
is_active = transform_boolean("1")  # True
is_active = transform_boolean("false")  # False

# UUID transformation
user_id = transform_uuid("550e8400-e29b-41d4-a716-446655440000")

# Datetime transformation
ts = transform_datetime_seconds_int(1704067200)  # datetime object
iso_str = transform_datetime_iso_milliseconds_zulu(dt)  # "2024-01-01T00:00:00.000Z"

# List transformations
ids = tf_list_int("1,2,3")  # [1, 2, 3]
tags = tf_list_string("a,b,c")  # ["a", "b", "c"]
```

### Usage with dpath_value

```python
from functools import partial

from lamb.utils import dpath_value
from lamb.utils.validators import validate_string, validate_email
from lamb.utils.transformers import transform_string_enum
from modules.core.models import UserStatus


@rest_allowed_http_methods(["POST"])
class UserCreateView(RestView):
    async def post(self, request):
        json_body = parse_body_as_json(request)

        # Use dpath_value with validators and transformers
        username = dpath_value(
            json_body,
            "username",
            str,
            transform=validate_string,
            transform_kwargs={"min_length": 3, "max_length": 50},
        )

        email = dpath_value(
            json_body,
            "email",
            str,
            transform=validate_email,
        )

        # Option 1: Using transform_kwargs with transform_string_enum
        status = dpath_value(
            json_body,
            "status",
            str,
            transform=transform_string_enum,
            transform_kwargs={"enum_class": UserStatus},
            default=UserStatus.ACTIVE,
        )

        # Option 2: Using functools.partial for pre-configured transformers
        transform_user_status = partial(transform_string_enum, enum_class=UserStatus)
        status = dpath_value(
            json_body,
            "status",
            str,
            transform=transform_user_status,
            default=UserStatus.ACTIVE,
        )

        # Create user
        user = User(username=username, email=email, status=status)
        await request.lamb_db_session.add(user)
        await request.lamb_db_session.commit()

        return user
```

#### Creating Custom Transformers

Common use case: creating transformers for enum types that are reused across the project.

```python
# modules/core/transformers.py
from functools import partial
from typing import Type

from lamb.exc import InvalidParamValueError
from lamb.utils.transformers import transform_string_enum
from modules.core.models import UserRole

# Pre-configure transformers for common enums using functools.partial
tf_user_role = partial(transform_string_enum, enum_class=UserRole)(value)


# Function styled classic transformer
def tf_notification_type(value: str) -> "NotificationType":
    """Transform string to NotificationType enum."""
    from modules.core.models import NotificationType

    return transform_string_enum(value, enum_class=NotificationType)


# Usage in views
from lamb.utils import dpath_value

role = dpath_value(
    json_body,
    "role",
    str,
    transform=tf_user_role,
    default=UserRole.USER,
)

notification_type = dpath_value(
    json_body,
    "type",
    str,
    transform=tf_notification_type,
)
```

---

## 6. dpath_value Utility

### Description

`dpath_value` provides safe nested dictionary access with type conversion, validation, and transformation support.

### Signature

```python
def dpath_value(
        obj: dict | os._Environ | settings,
        path: str | list[str],
        req_type: type,
        default: Any = None,
        transform: Callable | None = None,
        transform_kwargs: dict | None = None,
        allow_none: bool = False,
) -> Any
```

### Arguments

| Argument           | Type                       | Description                                                                |
|--------------------|----------------------------|----------------------------------------------------------------------------|
| `obj`              | dict, os.environ, settings | Source object (dict, environment, or Django settings)                      |
| `path`             | str or list[str]           | Access path (e.g., `'user.profile.name'` or `['user', 'profile', 'name']`) |
| `req_type`         | type                       | Expected type (str, int, float, bool, UUID, etc.)                          |
| `default`          | Any                        | Default value if path not found (default: `None`)                          |
| `transform`        | Callable                   | Optional transformation function                                           |
| `transform_kwargs` | dict                       | Keyword arguments for transform function                                   |
| `allow_none`       | bool                       | Allow `None` values (default: `False`)                                     |

### Supported Objects

- **dict**: Nested dictionaries
- **os.environ**: Environment variables
- **Django settings**: `django.conf.settings`
- **request.META**: HTTP headers and metadata

### Examples

```python
from lamb.utils import dpath_value
import os
from django.conf import settings

# Nested dict access
data = {"user": {"profile": {"name": "Alice", "age": 30}}}

name = dpath_value(data, "user.profile.name", str)  # "Alice"
age = dpath_value(data, "user.profile.age", int)  # 30
missing = dpath_value(data, "user.profile.email", str, default="unknown@unknown.com")

# Environment variables
api_key = dpath_value(os.environ, "API_KEY", str, default="default_key")

# Django settings
debug_mode = dpath_value(settings, "DEBUG", bool, transform=transform_boolean, default=False)

# request.META (HTTP headers)
device_family = dpath_value(request.META, "HTTP_X_LAMB_DEVICE_FAMILY", str, default=None)

# With transformation
tags = dpath_value(request.GET, "tags", str, transform=tf_list_string, default=[])

# With validation
user_id = dpath_value(json_body, "user.id", str, transform=validate_uuid, error_cls=InvalidBodyStructureError)
```

---

## 7. Filtering, Sorting, and Pagination

### 7.1. Filtering

#### Available Filters

Lamb provides the following built-in filters in `lamb.utils.filters`:

| Filter Type                      | Description                                  | Example                           | Use Case                                          |
|----------------------------------|----------------------------------------------|-----------------------------------|---------------------------------------------------|
| `ColumnValueFilter`              | Exact value match (supports multiple values) | `status=active`                   | Filter by exact field value                       |
| `ColumnBooleanFilter`            | Boolean field filter                         | `is_used=true`                    | Filter boolean columns                            |
| `EnumFilter`                     | Enum field filter with auto-transform        | `status=active`                   | Filter enum fields (auto-converts string to enum) |
| `DateFilter`                     | Date field filter with ISO parsing           | `created_date=2024-01-15`         | Filter by date                                    |
| `DatetimeFilter`                 | Datetime field filter with ISO parsing       | `created_at=2024-01-15T10:30:00Z` | Filter by datetime                                |
| `JsonDataFilter`                 | JSONB field filtering with descriptors       | `metadata.role==admin`            | Filter JSONB columns                              |
| `PostgresqlFastTextSearchFilter` | PostgreSQL full-text search                  | `q=hello%20world`                 | Full-text search                                  |

**Note:** For range/in/list filters, use manual `query.where()` conditions with `dpath_value` extraction (see example
below).

#### Filter Usage Example with SQLAlchemy 2.0 Select

```python
from functools import partial

from lamb.utils import dpath_value, response_filtered
from lamb.utils.filters import ColumnBooleanFilter, ColumnValueFilter, EnumFilter, DatetimeFilter
from modules.core.models import User
from modules.core.filters import DatetimeFilter as CustomDatetimeFilter
from modules.core.schemas import UserStatus


@rest_allowed_http_methods(["GET"])
class UserListView(RestView):
    async def get(self, request):
        db_session = request.lamb_db_session

        # Option 1: Using built-in filters with response_filtered
        filters = [
            ColumnBooleanFilter(User.is_active, arg_name="is_active"),
            EnumFilter(User.role, arg_name="role"),  # Auto-transforms string to enum
            CustomDatetimeFilter(User.time_created, arg_name="created_after"),
            ColumnValueFilter(User.age),  # supports quantifiers - age.min/age.max/age.greater...
        ]

        query = select(User)
        query = response_filtered(query=query, filters=filters, params=request.GET)

        # Option 2: Manual filtering with dpath_value (for complex conditions)
        status = dpath_value(request.GET, "status", str, default=None)
        if status:
            query = query.where(User.status == status)

        # Multiple values (comma-separated)
        roles = dpath_value(request.GET, "roles", str, default=None)
        if roles:
            role_list = [r.strip() for r in roles.split(",")]
            query = query.where(User.role.in_(role_list))

        # Result pagination
        result = await a_response_paginated(
            collection=query,
            params=request.GET,
            db_session=db_session,
        )

        return result
```

#### Custom Filter Example: ArrayEnumFilter

For filtering array/JSONB fields containing enum values:

```python
# modules/core/contrib/filters.py
from functools import partial

from lamb.utils import filters
from lamb.utils.transformers import transform_string_enum

from modules.core.schemas import TagType


class ArrayEnumFilter(filters.ColumnValueFilter):
    """Filter for array/JSONB fields containing enum values."""

    match_null: bool = False

    def __init__(self, *args, enum_class, match_null: bool = False, **kwargs):
        super().__init__(
            *args,
            req_type=str,
            req_type_transformer=partial(transform_string_enum, enum_class=enum_class),
            **kwargs,
        )
        self.match_null = match_null

    def apply_to_query(self, query, params, **kwargs):
        param_value = self.get_param_value(params, key_path=self.arg_name)
        if param_value is None:
            return query

        # Build WHERE clause for array contains
        for enum_value in param_value:
            if enum_value is None:
                if self.match_null:
                    query = query.where(self.comparing_field.is_(None))
            else:
                # For PostgreSQL array: column @> ARRAY['value']
                from sqlalchemy.dialects.postgresql import array

                query = query.where(self.comparing_field.overlap(array(enum_value)))

        return query
```

**Request Examples:**

```
GET /api/users/?is_active=true&role=admin&created_after=2024-01-01T00:00:00Z
GET /api/users/?status=active&roles=admin,moderator
GET /api/users/?age.gte=18&age.lte=65
```

---

### 7.2. Sorting

```python
from lamb.utils import response_sorted
from modules.core.models import User


@rest_allowed_http_methods(["GET"])
class UserListView(RestView):
    async def get(self, request):
        db_session = request.lamb_db_session

        # Define sorting via params: ?sorting=time_created{asc},user_role{desc}
        query = select(User)
        query = response_sorted(
            query,
            model_class=User,
            params=request.GET,
            default_sorting="created_at{desc}",  # default: newest first
        )

        users = await db_session.scalars(query).all()
        return {"users": users}
```

**Request Examples:**

```
GET /api/users/?sorting=created_at{asc}           # ascending
GET /api/users/?sorting=created_at{desc}          # descending (newest first)
GET /api/users/?sorting=created_at{desc},id{asc}  # multi-sort
```

**Response:**

```json
{
  "users": [
    {
      "id": 3,
      "username": "charlie",
      "created_at": "2024-01-15T10:00:00Z"
    },
    {
      "id": 1,
      "username": "alice",
      "created_at": "2024-01-14T10:00:00Z"
    },
    {
      "id": 2,
      "username": "bob",
      "created_at": "2024-01-14T09:00:00Z"
    }
  ]
}
```

---

### 7.3. Pagination

#### Async Pagination (recommended for async views)

```python
from lamb.utils import a_response_paginated
from modules.core.models import User


@rest_allowed_http_methods(["GET"])
class UserListView(RestView):
    async def get(self, request):
        db_session = request.lamb_db_session

        # Build query
        query = select(User)

        # Paginate
        pagination_result = await a_response_paginated(
            collection=query,
            params=request.GET,  # or explicit: params={"offset": 0, "limit": 20}
            db_session=db_session,
        )

        return pagination_result
```

**Request Examples:**

```
GET /api/users/?offset=0&limit=20
GET /api/users/?offset=20&limit=20
GET /api/users/?omit_total=true&offset=0&limit=100  # skip COUNT query
```

**Response:**

```json
{
  "total_count": 150,
  "offset": 0,
  "limit": 20,
  "items": [
    {
      "id": 1,
      "username": "alice"
    },
    {
      "id": 2,
      "username": "bob"
    },
    ...
  ]
}
```

#### Sync Pagination (for legacy sync views)

```python
from lamb.utils import response_paginated


@rest_allowed_http_methods(["GET"])
class UserListView(RestView):
    def get(self, request):
        db_session = request.lamb_db_session

        # Build query
        query = db_session.query(User)

        # Paginate
        pagination_result = response_paginated(
            data=query,
            request=request,
        )

        return pagination_result
```

---

#### ⚠️ NOTABENE: `total_omit` for DB Load Reduction

The `total_omit` parameter (or `omit_total=true` in query params) **completely skips the COUNT query** to the database:

| Parameter                    | COUNT Query | When to Use                                           |
|------------------------------|-------------|-------------------------------------------------------|
| `total_omit=false` (default) | ✅ Executed | When you need pagination with "pages" and total count |
| `total_omit=true`            | ❌ Skipped  | Infinite scroll, "Load more", streaming processing    |

**Advantages of `total_omit=true`:**

- **Radical DB load reduction**: Eliminates heavy `COUNT(*)` query, especially critical for large tables (millions of
  rows)
- **Faster response time**: No waiting for COUNT before returning data
- **No locking**: Tables are not locked during COUNT in some DBMS

**Disadvantages:**

- `total_count` in response will be `null`
- Cannot show "Page 5 of 42"
- Client must handle `null` or use "Load more" pattern

**Example for infinite scroll:**

```python
@rest_allowed_http_methods(["GET"])
class FeedListView(RestView):
    async def get(self, request):
        db_session = request.lamb_db_session

        # Infinite scroll: omit total for performance
        pagination_result = await a_response_paginated(
            collection=select(Post).join(User),
            params=request.GET,  # client sends: ?offset=0&limit=20&omit_total=true
            db_session=db_session,
        )

        # total_count will be None
        # {"total_count": null, "offset": 0, "limit": 20, "items": [...]}

        return pagination_result
```

**Default configuration in `lamb/settings.py`:**

```python
LAMB_PAGINATION_KEY_TOTAL = "total_count"
LAMB_PAGINATION_KEY_OMIT_TOTAL = "total_omit"
LAMB_PAGINATION_LIMIT_DEFAULT = 100
LAMB_PAGINATION_LIMIT_MAX = 5000
```

**Validation of `total_omit`:**

```python
from lamb.utils.transformers import transform_boolean
from lamb.utils import dpath_value

total_omit = dpath_value(
    params,
    settings.LAMB_PAGINATION_KEY_OMIT_TOTAL,
    str,
    transform=transform_boolean,
    default=False,  # COUNT by default
)
```

---

### 7.4. Combined Example: Filter + Sort + Paginate

```python
from lamb.utils import response_sorted, a_response_paginated
from lamb.utils import dpath_value
from modules.core.models import User


@rest_allowed_http_methods(["GET"])
class UserListView(RestView):
    async def get(self, request):
        db_session = request.lamb_db_session

        # 1. Build base query
        query = select(User)

        # 2. Apply filters manually
        status = dpath_value(request.GET, "status", str, default=None)
        if status:
            query = query.where(User.status == status)

        # 3. Apply sorting
        query = response_sorted(
            query,
            model_class=User,
            params=request.GET,
            default_sorting="created_at{desc}",
        )

        # 4. Apply pagination
        pagination_result = await a_response_paginated(
            collection=query,
            params=request.GET,
            db_session=db_session,
        )

        return pagination_result
```

**Request:**

```
GET /api/users/?status=active&age.gte=18&sorting=created_at{desc}&offset=0&limit=10
```

**Response:**

```json
{
  "total_count": 45,
  "offset": 0,
  "limit": 10,
  "items": [
    {
      "id": 10,
      "username": "alice",
      "status": "active",
      "created_at": "2024-01-15T10:00:00Z"
    },
    {
      "id": 11,
      "username": "bob",
      "status": "active",
      "created_at": "2024-01-14T10:00:00Z"
    },
    ...
  ]
}
```

---

## 8. Middleware Reference

### Available Middleware Classes

| Middleware                    | Purpose                                                                                                                                                                                                               |
|-------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `LambXRayMiddleware`          | Generates `xray` (unique per request) and `xline` (logical grouping) UUIDs from headers or random values. Attached to `request.xray` and `request.xline` for tracing and logging correlation.                         |
| `LambGRequestMiddleware`      | Stores the "current" request in a context variable, allowing access to the request from anywhere in the code without passing it explicitly. Provides `get_request()`, `set_request()`, and `del_request()` utilities. |
| `LambSQLAlchemyMiddleware`    | Injects `request.lamb_db_session` for database access. Handles session lifecycle (creation, commit, rollback).                                                                                                        |
| `LambRestApiJsonMiddleware`   | Automatically serializes response data to JSON. Handles exceptions and error responses with proper status codes and error codes.                                                                                      |
| `LambDeviceInfoMiddleware`    | Parses device info headers (`HTTP_X_LAMB_DEVICE_*`) and attaches `request.lamb_device_info` with device family, platform, OS, locale, app version, IP, and GeoIP data.                                                |
| `LambExecutionTimeMiddleware` | Collects request execution time metrics, logs them, and optionally stores them in TimescaleDB for performance monitoring.                                                                                             |
| `LambCorsMiddleware`          | Adds CORS headers based on `LAMB_ADD_CORS_*` settings. **Note:** Primarily useful in development. In production, configure CORS at the load balancer/reverse proxy level (e.g., NGINX, AWS ALB, CloudFlare).          |

### Middleware Order Example

```python
MIDDLEWARE = [
    "lamb.middleware.xray.LambXRayMiddleware",  # Tracing first - generates xray/xline IDs
    "lamb.middleware.grequest.LambGRequestMiddleware",  # Request context for global access
    "django.middleware.common.CommonMiddleware",
    "lamb.middleware.device_info.LambDeviceInfoMiddleware",  # Device info parsing
    "lamb.middleware.db.LambSQLAlchemyMiddleware",  # DB session injection
    "lamb.rest.middleware.LambRestApiJsonMiddleware",  # JSON response serialization
    "lamb.middleware.execution_time.LambExecutionTimeMiddleware",  # Performance metrics
]
```

---

## 9. Logging & X-Ray/XLine

### Sample Log Output

```
2024-01-15T10:30:45.123Z INFO [<LambXRayMiddleware>] Did attach x-fields to request: xray=a1b2c3d4-e5f6-7890-abcd-ef1234567890, xline=None
2024-01-15T10:30:45.125Z DEBUG [<LambDeviceInfoMiddleware>] attached: device_info=DeviceInfo(device_family='iPhone', device_platform='ios', device_os='17.2', ...)
2024-01-15T10:30:45.456Z INFO request completed: xray=a1b2c3d4-e5f6-7890-abcd-ef1234567890, method=GET, path=/api/users/, status=200, duration_ms=331
```

### X-Ray / XLine Fields

| Field   | Source                                   | Purpose                                                                             | Example                                |
|---------|------------------------------------------|-------------------------------------------------------------------------------------|----------------------------------------|
| `xray`  | `HTTP_X_LAMB_XRAY` header or random UUID | Unique identifier for a single request. Used for tracing and log correlation.       | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `xline` | `HTTP_X_LAMB_XLINE` header or None       | Logical grouping of related requests (e.g., batch operations, microservice chains). | `b2c3d4e5-f6a7-8901-bcde-f12345678901` |

### Configuration

```python
# settings.py
LAMB_LOG_HEADER_XRAY = "HTTP_X_LAMB_XRAY"  # Header name for xray
LAMB_LOG_HEADER_XLINE = "HTTP_X_LAMB_XLINE"  # Header name for xline
LAMB_LOG_XHEADERS_NAMESPACE = uuid.NAMESPACE_OID  # UUID namespace for hashing xline
```

### Using X-Ray in Logs

```python
import logging

logger = logging.getLogger(__name__)


@rest_allowed_http_methods(["GET"])
class UserView(RestView):
    async def get(self, request, user_id):
        # Access xray/xline from request
        logger.info(f"Fetching user: xray={request.xray}, user_id={user_id}")

        # X-ray is automatically included in log context by LambGRequestMiddleware
        user = await get_user(user_id)
        return user
```

---

## 11. Settings Reference

Complete reference of all `LAMB_*` configuration options available in `settings.py`.

### Configuration Table

| Setting                                | Type                   | Description                                                                                                        |
|----------------------------------------|------------------------|--------------------------------------------------------------------------------------------------------------------|
| `LAMB_DB_CONFIG`                       | `dict`                 | SQLAlchemy database configurations. Keys: `"default"`, `"replica"`, etc. Each value: `{"url": "postgresql://..."}` |
| `LAMB_REDIS_CONFIG`                    | `dict[RedisConfig]`    | Redis configurations for different purposes. Keys: `"s-cache"`, `"a-broker"`, `"a-throttling"`, etc.               |
| `LAMB_S3_CONFIG`                       | `dict[S3BucketConfig]` | S3 bucket configurations. Keys: bucket names (e.g., `"default"`, `"avatars"`, `"documents"`)                       |
| `LAMB_BROKER_URL`                      | `str`                  | Celery broker URL (derived from `LAMB_REDIS_CONFIG["a-broker"].broker_url`)                                        |
| `LAMB_BROKER_RESULT_URL`               | `str`                  | Celery result backend URL (derived from `LAMB_REDIS_CONFIG["a-result"].broker_url`)                                |
| `LAMB_BROKER_TRANSPORT_OPTIONS`        | `dict`                 | Celery broker transport options (derived from Redis config)                                                        |
| `LAMB_BROKER_RESULT_TRANSPORT_OPTIONS` | `dict`                 | Celery result backend transport options (derived from Redis config)                                                |
| `LAMB_LOG_JSON_ENABLE`                 | `bool`                 | Enable JSON format for logs                                                                                        |
| `LAMB_LOG_JSON_HIDE`                   | `list[str]`            | Fields to hide in JSON logs                                                                                        |
| `LAMB_LOG_FORMAT_TIME_ZONE`            | `str`                  | Timezone for log timestamps                                                                                        |
| `LAMB_LOG_HEADER_XRAY`                 | `str`                  | Header name for X-Ray tracing ID                                                                                   |
| `LAMB_LOG_HEADER_XLINE`                | `str`                  | Header name for X-Line logical grouping ID                                                                         |
| `LAMB_LOG_SQL_VERBOSE`                 | `bool`                 | Enable verbose SQL logging                                                                                         |
| `LAMB_LOG_SQL_VERBOSE_THRESHOLD`       | `float`                | Threshold in seconds for slow SQL logging                                                                          |
| `LAMB_EXECUTION_TIME_STORE`            | `bool`                 | Store execution time metrics in database                                                                           |
| `LAMB_EXECUTION_TIME_SKIP_METHODS`     | `list[str]`            | HTTP methods to skip for execution time tracking                                                                   |
| `LAMB_ADD_CORS_ENABLED`                | `bool`                 | Enable CORS headers (development only)                                                                             |
| `LAMB_DEVICE_INFO_COLLECT_IP`          | `bool`                 | Collect client IP address from device info                                                                         |
| `LAMB_DEVICE_INFO_COLLECT_GEO`         | `bool`                 | Collect GeoIP data from device info                                                                                |
| `LAMB_DEVICE_INFO_LOCALE_VALID_SEPS`   | `tuple[str]`           | Valid separators for locale parsing                                                                                |
| `LAMB_DEVICE_INFO_CLASS`               | `str`                  | Device info class path                                                                                             |
| `LAMB_DPATH_DICT_ENGINE`               | `str`                  | Engine for `dpath_value` dictionary access                                                                         |
| `LAMB_RESPONSE_EXCEPTION_SERIALIZER`   | `str`                  | Exception serializer class path                                                                                    |
| `LAMB_APP_DEV_MODE`                    | `bool`                 | Development mode flag                                                                                              |
| `LAMB_APP_GOD_MODE`                    | `bool`                 | God mode (superuser privileges) flag                                                                               |
| `LAMB_APP_RUNNER`                      | `str`                  | ASGI runner: `"granian"` or `"daphne"`                                                                             |
| `LAMB_APP_SCHEME`                      | `str`                  | Application scheme for URLs                                                                                        |
| `LAMB_SYSTEM_STATIC_FOLDER`            | `Path`                 | System static files folder path                                                                                    |
| `LAMB_STATIC_FOLDER`                   | `Path`                 | Application static files folder path                                                                               |
| `LAMB_TEMPLATE_FOLDER`                 | `Path`                 | Templates folder path                                                                                              |
| `LAMB_CRT_FOLDER`                      | `Path`                 | Certificates folder path                                                                                           |

### Device Info Headers

Device info is collected from HTTP headers with `HTTP_X_` prefix and `_` separator (Django convention):

| Django Header (`request.META`)   | Client Header               | Setting | Description                                     |
|----------------------------------|-----------------------------|---------|-------------------------------------------------|
| `HTTP_X_LAMB_DEVICE_FAMILY`      | `X-Lamb-Device-Family`      | —       | Device family (e.g., "iPhone", "Samsung")       |
| `HTTP_X_LAMB_DEVICE_PLATFORM`    | `X-Lamb-Device-Platform`    | —       | Platform: "ios", "android", "web"               |
| `HTTP_X_LAMB_DEVICE_OS`          | `X-Lamb-Device-Os`          | —       | OS version (e.g., "17.2", "14")                 |
| `HTTP_X_LAMB_DEVICE_LOCALE`      | `X-Lamb-Device-Locale`      | —       | Locale (e.g., "en_US", "ru-RU")                 |
| `HTTP_X_LAMB_DEVICE_APP_VERSION` | `X-Lamb-Device-App-Version` | —       | App version (e.g., "2.4.1")                     |
| `HTTP_X_LAMB_DEVICE_APP_BUILD`   | `X-Lamb-Device-App-Build`   | —       | App build number (e.g., 241)                    |
| `HTTP_X_LAMB_DEVICE_APP_ID`      | `X-Lamb-Device-App-Id`      | —       | App bundle/identifier (e.g., "com.example.app") |

---

## 12. Release Notes

See the [release notes](release_notes.md) or check the git history for the complete list of changes.
