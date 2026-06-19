#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups/$(date +%Y%m%d)"
RETENTION_DAYS=${RETENTION_DAYS:-30}
S3_BUCKET=${S3_BUCKET:-"s3://aeroforge-x-backups"}

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

echo "[$(date)] Backing up PostgreSQL..."
pg_basebackup -h "${PG_HOST}" -U aeroforge -D "${BACKUP_DIR}/pg_base" -Ft -z -P
pg_dumpall -h "${PG_HOST}" -U aeroforge | gzip > "${BACKUP_DIR}/pg_full_$(date +%Y%m%d_%H%M%S).sql.gz"

echo "[$(date)] Backing up Neo4j..."
neo4j-admin database dump neo4j --to-stdout | gzip > "${BACKUP_DIR}/neo4j_dump_$(date +%Y%m%d_%H%M%S).dump.gz"

echo "[$(date)] Backing up MinIO..."
mc mirror --watch --remove local-minio/ "${S3_BUCKET}/minio/"

echo "[$(date)] Uploading backups to S3..."
aws s3 sync "${BACKUP_DIR}" "${S3_BUCKET}/daily/$(date +%Y%m%d)/"

echo "[$(date)] Cleaning old backups (retention: ${RETENTION_DAYS} days)..."
find /backups -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} + 2>/dev/null || true
aws s3 ls "${S3_BUCKET}/daily/" | while read -r line; do
  dir_date=$(echo "$line" | awk '{print $2}' | tr -d '/')
  if [[ -n "$dir_date" ]]; then
    dir_epoch=$(date -d "$dir_date" +%s 2>/dev/null || echo "0")
    cutoff_epoch=$(date -d "${RETENTION_DAYS} days ago" +%s 2>/dev/null || echo "0")
    if [[ "$dir_epoch" -lt "$cutoff_epoch" ]] && [[ "$dir_epoch" -gt 0 ]]; then
      aws s3 rm --recursive "${S3_BUCKET}/daily/${dir_date}"
    fi
  fi
done

echo "[$(date)] Backup completed successfully"