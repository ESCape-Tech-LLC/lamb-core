#!/bin/bash
# scripts/start-test-env.sh
# Starts the test environment with clean initialization

set -e

COMPOSE_FILE="docker-compose.test.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================="
echo "🚀 Lamb-core Test Environment"
echo "========================================="
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Clean up existing containers/volumes
echo "🧹 Cleaning up existing test environment..."
docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
echo "✅ Cleanup done"
echo ""

# Start Docker services
echo "📦 Starting Docker services..."
docker compose -f "$COMPOSE_FILE" up -d
echo ""

# Brief pause to allow healthchecks to initialize
echo "⏳ Allowing healthchecks to initialize (10s)..."
sleep 10
echo ""

# Export COMPOSE_FILE for wait-for-healthy.sh
export COMPOSE_FILE

# Wait for services to be ready using health check script
echo "⏳ Waiting for services to be healthy..."
echo ""

# Wait for each service using wait-for-healthy.sh
if ! "${SCRIPT_DIR}/wait-for-healthy.sh" postgres 120; then
    echo "❌ PostgreSQL failed to become healthy" >&2
    exit 1
fi
echo "   PostgreSQL (35432)... ✅"

if ! "${SCRIPT_DIR}/wait-for-healthy.sh" valkey 120; then
    echo "❌ Valkey standalone failed to become healthy" >&2
    exit 1
fi
echo "   Valkey standalone (36379)... ✅"

# Valkey Sentinel
if ! "${SCRIPT_DIR}/wait-for-healthy.sh" valkey-sentinel-master 120; then
    echo "❌ Valkey Sentinel master failed to become healthy" >&2
    exit 1
fi
echo "   Valkey Sentinel master (36380)... ✅"

if ! "${SCRIPT_DIR}/wait-for-healthy.sh" valkey-sentinel-replica 120; then
    echo "❌ Valkey Sentinel replica failed to become healthy" >&2
    exit 1
fi
echo "   Valkey Sentinel replica (36381)... ✅"

if ! "${SCRIPT_DIR}/wait-for-healthy.sh" valkey-sentinel-1 120; then
    echo "❌ Valkey Sentinel failed to become healthy" >&2
    exit 1
fi
echo "   Valkey Sentinel (36382)... ✅"

# Valkey Cluster
for i in 1 2 3; do
    if ! "${SCRIPT_DIR}/wait-for-healthy.sh" valkey-cluster-node-$i 120; then
        echo "❌ Valkey Cluster node-$i failed to become healthy" >&2
        exit 1
    fi
done
echo "   Valkey Cluster nodes (36390-36392)... ✅"

# Initialize Valkey Cluster
echo "🔗 Initializing Valkey Cluster..."
if ! docker compose -f "$COMPOSE_FILE" exec -T valkey-cluster-node-1 valkey-cli \
    -a testpass123 --cluster create \
    valkey-cluster-node-1:6379 valkey-cluster-node-2:6379 valkey-cluster-node-3:6379 \
    --cluster-replicas 0 --cluster-yes 2>/dev/null; then
    echo "⚠️  Cluster may already be initialized, checking status..."
fi

# Allow cluster to stabilize
echo "⏳ Waiting for cluster to stabilize (5s)..."
sleep 5

# Verify cluster is ready
for i in 1 2 3; do
    CLUSTER_STATE=$(docker compose -f "$COMPOSE_FILE" exec -T valkey-cluster-node-$i \
        valkey-cli -a testpass123 cluster info 2>/dev/null | grep cluster_state | cut -d: -f2 | tr -d '\r\n')
    if [ "$CLUSTER_STATE" != "ok" ]; then
        echo "❌ Valkey Cluster node-$i not ready (state: $CLUSTER_STATE)" >&2
        exit 1
    fi
done
echo "✅ Valkey Cluster initialized and ready"

if ! "${SCRIPT_DIR}/wait-for-healthy.sh" minio 120; then
    echo "❌ MinIO failed to become healthy" >&2
    exit 1
fi
echo "   MinIO (39000)... ✅"

if ! "${SCRIPT_DIR}/wait-for-healthy.sh" kafka-1 180; then
    echo "❌ Kafka failed to become healthy" >&2
    exit 1
fi
if ! "${SCRIPT_DIR}/wait-for-healthy.sh" kafka-2 180; then
    echo "❌ Kafka failed to become healthy" >&2
    exit 1
fi
echo "   Kafka (39092-39093)... ✅"

echo ""

# Initialize MinIO buckets
echo "🪣 Initializing MinIO buckets..."
docker compose -f "$COMPOSE_FILE" exec -T minio mc mb -p local/test-bucket 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" exec -T minio mc mb -p local/test-bucket-private 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" exec -T minio mc anonymous set download local/test-bucket 2>/dev/null || true
echo "✅ MinIO buckets created"
echo ""

# Create test topics in Kafka (optional)
echo "📬 Creating Kafka test topics..."
docker compose -f "$COMPOSE_FILE" exec -T kafka /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:39092 \
    --create --if-not-exists \
    --topic test-topic \
    --partitions 3 \
    --replication-factor 1 2>/dev/null || true
echo "✅ Kafka topics created"
echo ""

echo "========================================="
echo "✅ Test environment ready!"
echo "========================================="
echo ""
echo "📊 Services running:"
echo "   - PostgreSQL:          localhost:35432"
echo "   - Valkey standalone:   localhost:36379"
echo "   - Valkey Sentinel:     localhost:36380 (master), 36382 (sentinel)"
echo "   - Valkey Cluster:      localhost:36390-36392"
echo "   - MinIO API:           localhost:39000"
echo "   - MinIO UI:            http://localhost:39001"
echo "   - Kafka:               localhost:39092"
echo ""
echo "🔐 Credentials:"
echo "   - PostgreSQL: lamb_test / lamb_test_pass"
echo "   - Valkey:     testpass123"
echo "   - MinIO:      minio / minio123"
echo ""
echo "🧪 Run tests:"
echo "   uv run pytest tests/unit -v"
echo "   uv run pytest tests/integration -v -m integration"
echo "   uv run pytest tests/ -v --cov=lamb --cov-report=html"
echo ""
echo "🛑 Stop environment:"
echo "   ./scripts/stop-test-env.sh"
echo ""