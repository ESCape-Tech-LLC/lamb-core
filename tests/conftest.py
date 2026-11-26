"""
Pytest fixtures for lamb-core test suite.

Provides fixtures for database, Redis, Kafka, and MinIO/S3 services.
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.test_settings")

import django
django.setup()

import pytest
from typing import Generator, AsyncGenerator

import redis
import redis.asyncio as redis_asyncio

from lamb.db.context import lamb_db_context
from lamb.service.redis.config import RedisConfig, Mode
from lamb.service.kafka.config import KafkaConfig


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def db_config_dict():
    """Database configuration dict for tests.
    
    Returns connection parameters for PostgreSQL 18 with TimescaleDB.
    """
    return {
        "host": "localhost",
        "port": 35432,
        "db_name": "lamb_test",
        "username": "lamb_test",
        "password": "lamb_test_pass",
    }


@pytest.fixture(scope="function")
def db_context(db_config_dict):
    """Sync database context fixture using lamb_db_context.
    
    Usage::
    
        def test_something(db_context):
            db_context.execute(...)
            db_context.commit()
    """
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.test_settings")
    
    import django
    django.setup()
    
    ctx = lamb_db_context(pooled=False, db_key="default")
    with ctx as session:
        yield session


@pytest.fixture(scope="function")
async def async_db_context(db_config_dict):
    """Async database context fixture using lamb_db_context.
    
    Usage::
    
        @pytest.mark.asyncio
        async def test_something(async_db_context):
            await async_db_context.execute(...)
            await async_db_context.commit()
    """
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.test_settings")
    
    import django
    django.setup()
    
    ctx = lamb_db_context(pooled=False, db_key="default")
    async with ctx as session:
        yield session


@pytest.fixture(scope="function")
async def clean_database(async_db_context):
    """Clean database before each test by truncating tables.
    
    This fixture is optional and should be used when you need a clean database state.
    It will attempt to truncate known tables, but will not fail if tables don't exist.
    """
    from sqlalchemy import text
    
    # Try to truncate common tables - ignore errors if tables don't exist
    try:
        await async_db_context.execute(text("TRUNCATE TABLE lamb_execution_time_metric CASCADE;"))
    except Exception:
        pass  # Table might not exist
    
    await async_db_context.commit()
    yield async_db_context


# =============================================================================
# Redis Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def redis_config_dict():
    """Redis configuration dict for tests."""
    return {
        "host": "localhost",
        "port": 36379,
        "db": 0,
        "password": "testpass123",
    }


@pytest.fixture(scope="function")
def redis_config(redis_config_dict) -> RedisConfig:
    """RedisConfig fixture for Redis tests.
    
    Creates a RedisConfig with GENERIC mode for single-node Redis.
    """
    return RedisConfig(
        host=redis_config_dict["host"],
        port=redis_config_dict["port"],
        default_db=redis_config_dict["db"],
        password=redis_config_dict["password"],
        mode=Mode.GENERIC,
    )


@pytest.fixture(scope="function")
def redis_client(redis_config) -> Generator[redis.Redis, None, None]:
    """Sync Redis client fixture.
    
    Automatically flushes database before and after test.
    """
    client = redis_config.redis()
    client.flushdb()
    yield client
    client.flushdb()
    client.close()


@pytest.fixture(scope="function")
async def async_redis_client(redis_config) -> AsyncGenerator:
    """Async Redis client fixture.
    
    Automatically flushes database before and after test.
    """
    client = await redis_config.aredis()
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.close()


# =============================================================================
# Kafka Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def kafka_config() -> KafkaConfig:
    """Kafka configuration fixture for tests.
    
    Returns KafkaConfig for Kafka 3.9 on port 19092.
    """
    return KafkaConfig(
        bootstrap_servers=["localhost:39092"],
        security_protocol="PLAINTEXT",
    )


@pytest.fixture(scope="function")
def kafka_topic(kafka_config):
    """Create and cleanup a test Kafka topic.
    
    Creates 'test-topic' with 3 partitions before test,
    deletes it after test.
    """
    import subprocess
    
    topic_name = "test-topic"
    
    # Create topic
    subprocess.run([
        "docker", "compose", "-f", "docker-compose.test.yml", "exec", "-T", "kafka-1",
        "/opt/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", "localhost:39092",
        "--create", "--if-not-exists",
        "--topic", topic_name,
        "--partitions", "3",
        "--replication-factor", "1"
    ], capture_output=True)
    
    yield topic_name
    
    # Delete topic
    subprocess.run([
        "docker", "compose", "-f", "docker-compose.test.yml", "exec", "-T", "kafka-1",
        "/opt/kafka/bin/kafka-topics.sh",
        "--bootstrap-server", "localhost:39092",
        "--delete", "--if-exists",
        "--topic", topic_name
    ], capture_output=True)


# =============================================================================
# MinIO / S3 Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def minio_endpoint() -> str:
    """MinIO endpoint for tests."""
    return "http://localhost:39000"


@pytest.fixture(scope="session")
def minio_credentials() -> dict:
    """MinIO credentials for tests.
    
    Returns credentials for MinIO access.
    """
    return {
        "aws_access_key_id": "minio",
        "aws_secret_access_key": "minio123",
        "region_name": "us-east-1",
    }


@pytest.fixture(scope="function")
def s3_bucket(minio_endpoint, minio_credentials):
    """Create and cleanup a test S3 bucket in MinIO.
    
    Creates 'test-bucket' before test, deletes all objects and bucket after test.
    
    Usage::
    
        def test_upload(s3_bucket):
            s3_client = boto3.client(...)
            s3_client.put_object(Bucket=s3_bucket, ...)
    """
    import boto3
    
    bucket_name = "test-bucket"
    
    s3_client = boto3.client(
        "s3",
        endpoint_url=minio_endpoint,
        aws_access_key_id=minio_credentials["aws_access_key_id"],
        aws_secret_access_key=minio_credentials["aws_secret_access_key"],
        region_name=minio_credentials["region_name"],
    )
    
    try:
        s3_client.create_bucket(Bucket=bucket_name)
    except s3_client.exceptions.BucketAlreadyExists:
        pass
    
    yield bucket_name
    
    # Cleanup bucket
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if "Contents" in response:
            objects = [{"Key": obj["Key"]} for obj in response["Contents"]]
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": objects}
            )
        s3_client.delete_bucket(Bucket=bucket_name)
    except Exception:
        pass  # Bucket might not exist


@pytest.fixture(scope="function")
def s3_async_client(minio_endpoint, minio_credentials):
    """Async S3 client fixture for aioboto3.
    
    Returns a coroutine that creates an async S3 client.
    
    Usage::
    
        @pytest.mark.asyncio
        async def test_upload_async(s3_async_client):
            async with await s3_async_client() as client:
                await client.put_object(...)
    """
    import aioboto3
    
    session = aioboto3.Session()
    
    async def get_client():
        return await session.client(
            "s3",
            endpoint_url=minio_endpoint,
            aws_access_key_id=minio_credentials["aws_access_key_id"],
            aws_secret_access_key=minio_credentials["aws_secret_access_key"],
            region_name=minio_credentials["region_name"],
        )
    
    return get_client


# =============================================================================
# HTTP / aiohttp Fixtures
# =============================================================================

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession for unit tests.
    
    Provides async mock session with configurable responses.
    """
    from unittest.mock import AsyncMock, patch
    
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={})
        mock_response.text = AsyncMock(return_value="{}")
        mock_session.get.return_value = mock_response
        
        mock_session_class.return_value = mock_session
        yield mock_session


# =============================================================================
# Dpath Engine Fixtures
# =============================================================================


# =============================================================================
# Test Helpers
# =============================================================================

@pytest.fixture
def anyio_backend():
    """Enable async tests with anyio asyncio backend."""
    return "asyncio"