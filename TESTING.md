# Testing Guide

This document describes the testing infrastructure and conventions for the `lamb-core` project.

## Table of Contents

- [Test Environment](#test-environment)
- [Quick Start](#quick-start)
- [Test Fixtures](#test-fixtures)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [Troubleshooting](#troubleshooting)

## Test Environment

The test environment uses Docker Compose to provide real services for integration testing:

| Service | Version | Port | Purpose |
|---------|---------|------|---------|
| PostgreSQL 18 + TimescaleDB | latest-pg18 | 35432 | Database |
| Valkey bundle (standalone) | 9.1.1 | 36379 | Cache/Session |
| Valkey Sentinel | 9.1.1 | 36380-36382 | High availability |
| Valkey Cluster | 9.1.1 | 36390-36392 | Distributed cache |
| MinIO | latest | 39000/39001 | S3 Storage |
| Kafka Cluster | 3.9.1 | 39092-39093 | Event Streaming (2 nodes) |

All ports are in the 30000+ range to avoid conflicts with production services.

### Service Configuration

**PostgreSQL:**
- Database: `lamb_test`
- User: `lamb_test`
- Password: `lamb_test_pass`

**Valkey Standalone:**
- Password: `testpass123`
- Default DB: 0

**Valkey Sentinel:**
- Master port: 36380
- Replica port: 36381
- Sentinel port: 36382
- Password: `testpass123`
- Master name: `mymaster`

**Valkey Cluster:**
- Nodes: 36390, 36391, 36392
- Password: `testpass123"
- Cluster mode enabled

**MinIO:**
- Access Key: `minio`
- Secret Key: `minio123`
- Buckets: `test-bucket`, `test-bucket-private`

**Kafka Cluster:**
- Bootstrap servers: `localhost:39092,localhost:39093`
- Nodes: kafka-1 (39092), kafka-2 (39093)
- Mode: KRaft (no ZooKeeper)
- Replication factor: 2
- Security: PLAINTEXT

## Quick Start

### 1. Start Test Environment

```bash
./scripts/start-test-env.sh
```

This script will:
- Clean up any existing test containers
- Start all Docker services
- Wait for health checks
- Initialize MinIO buckets and Kafka topics

### 2. Install Test Dependencies

```bash
uv sync --group test
```

### 3. Run Tests

```bash
# Unit tests only
uv run pytest tests/unit -v

# Integration tests only
uv run pytest tests/integration -v -m integration

# All tests with coverage
uv run pytest tests/ -v --cov=lamb --cov-report=html
```

### 4. Stop Test Environment

```bash
./scripts/stop-test-env.sh
```

## Test Fixtures

All fixtures are defined in `tests/conftest.py`.

### Database Fixtures

**Sync Database Context:**
```python
def test_with_sync_db(db_context):
    """Use sync database context."""
    from sqlalchemy import text
    
    db_context.execute(text("SELECT 1"))
    db_context.commit()
```

**Async Database Context:**
```python
@pytest.mark.asyncio
async def test_with_async_db(async_db_context):
    """Use async database context."""
    from sqlalchemy import text
    
    await async_db_context.execute(text("SELECT 1"))
    await async_db_context.commit()
```

**Clean Database:**
```python
@pytest.mark.asyncio
async def test_with_clean_db(clean_database):
    """Use clean database fixture."""
    # Database will be truncated before test
    pass
```

### Valkey Fixtures

**Sync Valkey Client:**
```python
def test_valkey_sync(valkey_client):
    """Use sync Valkey client."""
    valkey_client.set("key", "value")
    assert valkey_client.get("key") == b"value"
```

**Async Valkey Client:**
```python
@pytest.mark.asyncio
async def test_valkey_async(async_valkey_client):
    """Use async Valkey client."""
    await async_valkey_client.set("key", "value")
    assert await async_valkey_client.get("key") == b"value"
```

### S3/MinIO Fixtures

**S3 Bucket:**
```python
def test_s3_operations(s3_bucket, minio_endpoint, minio_credentials):
    """Test S3 operations with MinIO."""
    import boto3
    
    s3_client = boto3.client(
        "s3",
        endpoint_url=minio_endpoint,
        aws_access_key_id=minio_credentials["aws_access_key_id"],
        aws_secret_access_key=minio_credentials["aws_secret_access_key"],
        region_name=minio_credentials["region_name"],
    )
    
    s3_client.put_object(Bucket=s3_bucket, Key="test.txt", Body=b"content")
```

**Async S3 Client:**
```python
@pytest.mark.asyncio
async def test_async_s3(s3_async_client, s3_bucket):
    """Test async S3 operations."""
    async with await s3_async_client() as client:
        await client.put_object(Bucket=s3_bucket, Key="async.txt", Body=b"content")
```

### Kafka Fixtures

**Kafka Topic:**
```python
def test_kafka_topic(kafka_topic, kafka_config):
    """Test with Kafka topic."""
    # Topic 'test-topic' is created and will be deleted after test
    pass
```

## Running Tests

### Test Markers

Use markers to categorize tests:

```python
import pytest


@pytest.mark.integration
def test_integration():
    """Integration test requiring Docker services."""
    pass


@pytest.mark.requires_db
def test_requires_database(db_context):
    """Test requiring database."""
    pass


@pytest.mark.requires_valkey
def test_requires_valkey(valkey_client):
    """Test requiring Valkey."""
    pass


@pytest.mark.requires_s3
def test_requires_s3(s3_bucket):
    """Test requiring S3."""
    pass


@pytest.mark.slow
def test_slow_operation():
    """Slow test (e.g., large data processing)."""
    pass
```

### Running Specific Test Types

```bash
# Only integration tests
uv run pytest tests/ -m integration

# Exclude slow tests
uv run pytest tests/ -m "not slow"

# Multiple markers
uv run pytest tests/ -m "integration and requires_db"

# Specific test file
uv run pytest tests/integration/test_valkey_basic.py -v

# Specific test method
uv run pytest tests/integration/test_valkey_basic.py::TestValkeyBasic::test_ping -v
```

### Coverage

Generate coverage report:

```bash
uv run pytest tests/ --cov=lamb --cov-report=html --cov-report=term-missing
```

Open coverage report:

```bash
open htmlcov/index.html  # macOS
```

## Test Categories

### Unit Tests

Located in `tests/unit/`:
- Test individual components in isolation
- No external dependencies
- Fast execution
- Use mocks for external services

```python
# tests/unit/test_utils.py
import pytest


class TestUtilityFunctions:
    """Unit tests for utility functions."""

    def test_helper_function(self):
        """Test a helper function."""
        from lamb.utils import helper

        result = helper("input")
        assert result == "expected"
```

### Integration Tests

Located in `tests/integration/`:
- Test integration with real services
- Require Docker test environment
- Slower than unit tests
- Use fixtures for service connections

```python
# tests/integration/test_db.py
import pytest
from sqlalchemy import text


@pytest.mark.integration
@pytest.mark.requires_db
class TestDatabaseIntegration:
    """Database integration tests."""

    def test_query(self, db_context):
        """Test database query."""
        result = db_context.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1
```

### API Tests

Located in `tests/api/`:
- Test REST API endpoints
- Use Django test client
- May require database

## Writing Tests

### Test Structure

```python
# tests/integration/test_service.py
import pytest


@pytest.mark.integration
class TestServiceName:
    """Tests for ServiceName."""

    def test_basic_operation(self, fixture1, fixture2):
        """Test basic operation."""
        # Arrange
        input_data = "test"

        # Act
        result = service_function(input_data)

        # Assert
        assert result == "expected"

    @pytest.mark.asyncio
    async def test_async_operation(self, async_fixture):
        """Test async operation."""
        result = await async_service_function("input")
        assert result == "expected"
```

### Best Practices

1. **Use descriptive test names:**
   ```python
   def test_upload_file_creates_object_in_bucket()  # Good
   def test_upload()  # Too vague
   ```

2. **One assertion per test (when possible):**
   ```python
   def test_upload_returns_200()  # Good
   def test_upload_returns_200_and_creates_object()  # Consider splitting
   ```

3. **Use fixtures for setup/teardown:**
   ```python
   @pytest.fixture
   def sample_data():
       return {"key": "value"}
   ```

4. **Mark async tests:**
   ```python
   @pytest.mark.asyncio
   async def test_async_function():
       pass
   ```

5. **Use integration marker for Docker-dependent tests:**
   ```python
   @pytest.mark.integration
   def test_with_docker_service():
       pass
   ```

## Troubleshooting

### Tests fail with connection errors

Make sure test environment is running:

```bash
./scripts/start-test-env.sh
```

Check if services are healthy:

```bash
docker compose -f docker-compose.test.yml ps
```

### Port conflicts

Check if ports are already in use:

```bash
lsof -i :35432  # PostgreSQL
lsof -i :36379  # Valkey standalone
lsof -i :36380  # Valkey Sentinel master
lsof -i :36390  # Valkey Cluster
lsof -i :39000  # MinIO
lsof -i :39092  # Kafka
```

### Docker services not healthy

Check service logs:

```bash
docker compose -f docker-compose.test.yml logs postgres
docker compose -f docker-compose.test.yml logs valkey
docker compose -f docker-compose.test.yml logs valkey-sentinel-master
docker compose -f docker-compose.test.yml logs valkey-cluster-node-1
docker compose -f docker-compose.test.yml logs minio
docker compose -f docker-compose.test.yml logs kafka-1
docker compose -f docker-compose.test.yml logs kafka-2
```

### Fixture not found

Make sure `tests/conftest.py` is in the correct location and pytest can discover it:

```bash
uv run pytest --collect-only tests/
```

### Database connection refused

Verify PostgreSQL is running and accessible:

```bash
psql -h localhost -p 35432 -U lamb_test -d lamb_test
```

### MinIO bucket creation fails

Check MinIO is accessible:

```bash
curl http://localhost:39000/minio/health/live
```

Manually create buckets:

```bash
./scripts/start-test-env.sh  # Re-run to initialize buckets
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: timescale/timescaledb:latest-pg18
        ports:
          - 35432:5432
        env:
          POSTGRES_USER: lamb_test
          POSTGRES_PASSWORD: lamb_test_pass
          POSTGRES_DB: lamb_test
      valkey:
        image: valkey/valkey-bundle:9.1.1
        ports:
          - 36379:6379
      minio:
        image: ghcr.io/coollabsio/minio:latest
        ports:
          - 39000:9000
          - 39001:9001
        env:
          MINIO_ROOT_USER: minio
          MINIO_ROOT_PASSWORD: minio123
      kafka:
        image: apache/kafka:3.9.1
        ports:
          - 39092:9092
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      
      - name: Install dependencies
        run: uv sync --group test
      
      - name: Run tests
        run: uv run pytest tests/ -v --cov=lamb --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [Docker Compose documentation](https://docs.docker.com/compose/)
- [pytest fixtures](https://docs.pytest.org/en/stable/explanation/fixtures.html)
- [pytest markers](https://docs.pytest.org/en/stable/example/markers.html)