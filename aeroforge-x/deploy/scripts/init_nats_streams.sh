#!/bin/sh
# AeroForge-X NATS JetStream Stream Initializer
# Waits for NATS to be healthy, then runs v6.0 and V6.1 stream init scripts

set -e

NATS_URL="${NATS_URL:-nats://nats:4222}"
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "[init-nats] Waiting for NATS at ${NATS_URL}..."

retries=0
while [ $retries -lt $MAX_RETRIES ]; do
    if wget --spider -q "http://nats:8222/healthz" 2>/dev/null || curl -sf "http://nats:8222/healthz" >/dev/null 2>&1; then
        echo "[init-nats] NATS is healthy"
        break
    fi
    retries=$((retries + 1))
    echo "[init-nats] Retry $retries/$MAX_RETRIES..."
    sleep $RETRY_INTERVAL
done

if [ $retries -eq $MAX_RETRIES ]; then
    echo "[init-nats] ERROR: NATS not healthy after $MAX_RETRIES retries"
    exit 1
fi

echo "[init-nats] Installing nats-py..."
pip install nats-py 2>/dev/null || pip3 install nats-py 2>/dev/null || true

echo "[init-nats] Running v6.0 stream initialization..."
python /migrations/v6_0/nats/init_v6_streams.py 2>/dev/null || \
python3 /migrations/v6_0/nats/init_v6_streams.py 2>/dev/null || \
echo "[init-nats] WARNING: v6.0 stream init failed (may already exist)"

echo "[init-nats] Running V6.1 stream initialization..."
python /migrations/v6_1/init_v61_streams.py 2>/dev/null || \
python3 /migrations/v6_1/init_v61_streams.py 2>/dev/null || \
echo "[init-nats] WARNING: V6.1 stream init failed (may already exist)"

echo "[init-nats] NATS stream initialization complete"