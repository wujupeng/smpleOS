#!/bin/sh
set -e

ENDPOINT="${MINIO_ENDPOINT:-minio:9000}"
USER="${MINIO_USER:-aeroforge}"
SECRET="${MINIO_SECRET:-aeroforge123}"

echo "Configuring mc alias for MinIO at ${ENDPOINT}"
mc alias set aeroforge http://${ENDPOINT} ${USER} ${SECRET} 2>/dev/null || {
    echo "ERROR: Failed to configure mc alias"
    exit 1
}

BUCKETS="aeroforge-cert-evidence aeroforge-dataset-artifacts aeroforge-mdo-results aeroforge-phm-models aeroforge-uq-reports aeroforge-gdt-annotations aeroforge-export-packages aeroforge-backups"

for BUCKET in ${BUCKETS}; do
    if mc ls aeroforge/${BUCKET} > /dev/null 2>&1; then
        echo "Bucket ${BUCKET} already exists (idempotent)"
    else
        mc mb aeroforge/${BUCKET} 2>/dev/null && echo "Bucket ${BUCKET} created" || echo "Bucket ${BUCKET} creation issue (may already exist)"
    fi
done

echo "MinIO bucket initialization complete"