#!/bin/sh
# AeroForge-X MinIO Bucket Initializer
# Waits for MinIO to be healthy, then creates required buckets

set -e

MINIO_ENDPOINT="${MINIO_ENDPOINT:-minio:9000}"
MINIO_USER="${MINIO_USER:-aeroforge}"
MINIO_SECRET="${MINIO_SECRET:-aeroforge123}"
MAX_RETRIES=30
RETRY_INTERVAL=2

REQUIRED_BUCKETS="
aeroforge-cert-evidence
aeroforge-dataset-artifacts
aeroforge-mdo-results
aeroforge-phm-models
aeroforge-uq-reports
aeroforge-gdt-annotations
aeroforge-export-packages
aeroforge-backups
"

echo "[init-minio] Waiting for MinIO at ${MINIO_ENDPOINT}..."

retries=0
while [ $retries -lt $MAX_RETRIES ]; do
    if curl -sf "http://${MINIO_ENDPOINT}/minio/health/live" >/dev/null 2>&1; then
        echo "[init-minio] MinIO is healthy"
        break
    fi
    retries=$((retries + 1))
    echo "[init-minio] Retry $retries/$MAX_RETRIES..."
    sleep $RETRY_INTERVAL
done

if [ $retries -eq $MAX_RETRIES ]; then
    echo "[init-minio] ERROR: MinIO not healthy after $MAX_RETRIES retries"
    exit 1
fi

echo "[init-minio] Installing mc client..."
if ! command -v mc >/dev/null 2>&1; then
    curl -sfL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc 2>/dev/null || \
    wget -q https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/local/bin/mc 2>/dev/null || true
    chmod +x /usr/local/bin/mc 2>/dev/null || true
fi

echo "[init-minio] Configuring mc alias..."
mc alias set aeroforge http://${MINIO_ENDPOINT} ${MINIO_USER} ${MINIO_SECRET} 2>/dev/null || \
    mc config host add aeroforge http://${MINIO_ENDPOINT} ${MINIO_USER} ${MINIO_SECRET} 2>/dev/null || true

for bucket in $REQUIRED_BUCKETS; do
    if mc ls aeroforge/${bucket} >/dev/null 2>&1; then
        echo "[init-minio] Bucket '${bucket}' already exists"
    else
        mc mb aeroforge/${bucket} 2>/dev/null && echo "[init-minio] Created bucket '${bucket}'" || \
            echo "[init-minio] WARNING: Failed to create bucket '${bucket}'"
    fi
done

echo "[init-minio] MinIO bucket initialization complete"