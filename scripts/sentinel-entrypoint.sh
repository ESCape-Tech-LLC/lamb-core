#!/bin/sh
# Get sentinel-master IP address
echo "Resolving sentinel-master IP..."
MASTER_IP=$(getent hosts sentinel-master | awk '{print $1; exit}')
if [ -z "$MASTER_IP" ]; then
    echo "❌ Failed to resolve sentinel-master, using fallback..."
    # Fallback: try to get from Docker network
    MASTER_IP=$(getent hosts lamb-core-valkey-sentinel-master-1 | awk '{print $1; exit}')
fi

if [ -z "$MASTER_IP" ]; then
    echo "❌ Cannot resolve sentinel-master hostname"
    exit 1
fi

echo "✅ sentinel-master resolved to $MASTER_IP"

# Wait for master to be reachable
echo "Waiting for master to respond..."
while ! valkey-cli -h "$MASTER_IP" -a testpass123 ping 2>/dev/null | grep -q PONG; do
    sleep 1
done
echo "✅ Master is reachable at $MASTER_IP"

# Generate sentinel config with IP
cat > /tmp/sentinel.conf <<EOF
sentinel myid 1234567890abcdef1234567890abcdef12345678
sentinel monitor mymaster $MASTER_IP 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1
sentinel auth-pass mymaster testpass123
EOF

echo "Starting Valkey Sentinel..."
exec valkey-sentinel /tmp/sentinel.conf
