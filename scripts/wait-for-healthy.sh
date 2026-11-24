#!/usr/bin/env bash
# scripts/wait-for-healthy.sh
# Wait for a Docker compose service to become healthy
#
# Usage: ./scripts/wait-for-healthy.sh <service-name> [timeout]
# Example: ./scripts/wait-for-healthy.sh postgres 120
#
# Exit codes:
#   0  - Service is healthy
#   1  - Timeout exceeded or service unhealthy
#   99 - Error (service not found, Docker not running, etc.)

set -e

# Get compose file from environment or use default
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.test.yml}"

service_name=$1
shift
timeout=$1

default_timeout=120

if [ -z "${timeout}" ]; then
    timeout=${default_timeout}
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first." >&2
    exit 99
fi

# Check if service exists in compose
if ! docker compose -f "$COMPOSE_FILE" ps -q "${service_name}" >/dev/null 2>&1; then
    echo "❌ Service '${service_name}' not found in compose." >&2
    echo "   Available services:" >&2
    docker compose -f "$COMPOSE_FILE" ps --format "table" >&2
    exit 99
fi

RETURN_HEALTHY=0
RETURN_STARTING=1
RETURN_UNHEALTHY=2
RETURN_UNKNOWN=3
RETURN_ERROR=99

function get_health_state {
    local container_id
    container_id=$(docker compose -f "$COMPOSE_FILE" ps -q "${service_name}")
    
    if [ -z "${container_id}" ]; then
        return ${RETURN_ERROR}
    fi
    
    state=$(docker inspect -f '{{ .State.Health.Status }}' "${container_id}" 2>/dev/null)
    return_code=$?
    
    if [ ! ${return_code} -eq 0 ]; then
        return ${RETURN_ERROR}
    fi
    
    if [[ "${state}" == "healthy" ]]; then
        return ${RETURN_HEALTHY}
    elif [[ "${state}" == "unhealthy" ]]; then
        return ${RETURN_UNHEALTHY}
    elif [[ "${state}" == "starting" ]]; then
        return ${RETURN_STARTING}
    else
        return ${RETURN_UNKNOWN}
    fi
}

function wait_for {
    echo "⏳ Waiting for '${service_name}' to be healthy (max ${timeout}s)..."
    
    for i in $(seq 1 ${timeout}); do
        get_health_state
        state=$?
        
        if [ ${state} -eq ${RETURN_HEALTHY} ]; then
            echo "✅ '${service_name}' is healthy after ${i}s"
            exit 0
        elif [ ${state} -eq ${RETURN_UNHEALTHY} ]; then
            echo "❌ '${service_name}' is unhealthy!" >&2
            echo "   Logs:" >&2
            docker compose -f "$COMPOSE_FILE" logs "${service_name}" >&2
            exit 1
        fi
        
        # Progress indicator every 5 seconds
        if [ $((i % 5)) -eq 0 ]; then
            echo -n "."
        fi
        
        sleep 1
    done
    
    echo ""
    echo "❌ Timeout exceeded (${timeout}s) waiting for '${service_name}'" >&2
    echo "   Current health status: $(docker inspect -f '{{ .State.Health.Status }}' $(docker compose -f "$COMPOSE_FILE" ps -q "${service_name}"))" >&2
    echo "   Logs:" >&2
    docker compose -f "$COMPOSE_FILE" logs "${service_name}" >&2
    exit 1
}

if [ -z "${service_name}" ]; then
    echo "❌ Service name is required." >&2
    echo "" >&2
    echo "Usage: $0 <service-name> [timeout]" >&2
    echo "" >&2
    echo "Example:" >&2
    echo "  $0 postgres 120" >&2
    echo "  $0 valkey 60" >&2
    echo "  $0 minio 120" >&2
    echo "  $0 kafka 180" >&2
    exit 1
else
    wait_for
fi
