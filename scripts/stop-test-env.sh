#!/bin/bash
# scripts/stop-test-env.sh
# Stops and cleans up the test environment

set -e

COMPOSE_FILE="docker-compose.test.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================="
echo "🛑 Stopping Test Environment"
echo "========================================="
echo ""

# Stop and remove containers and volumes
echo "🧹 Stopping containers and removing volumes..."
docker compose -f "$COMPOSE_FILE" down -v --remove-orphans

echo ""
echo "✅ Test environment stopped and cleaned up"
echo ""