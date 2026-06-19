#!/bin/bash
set -euo pipefail

PRIMARY_SITE=${PRIMARY_SITE:-"aeroforge-x.example.com"}
DR_SITE=${DR_SITE:-"aeroforge-x-dr.example.com"}
HEALTH_CHECK_URL="https://${PRIMARY_SITE}/health"
MAX_RETRIES=5
RETRY_INTERVAL=30

echo "[$(date)] DR Failover Check Starting..."

check_primary_health() {
  local retries=0
  while [ $retries -lt $MAX_RETRIES ]; do
    if curl -sf --max-time 10 "${HEALTH_CHECK_URL}" > /dev/null 2>&1; then
      echo "[$(date)] Primary site is healthy"
      return 0
    fi
    retries=$((retries + 1))
    echo "[$(date)] Primary site health check failed (attempt ${retries}/${MAX_RETRIES})"
    sleep $RETRY_INTERVAL
  done
  return 1
}

promote_dr_database() {
  echo "[$(date)] Promoting DR database cluster..."
  aws rds promote-read-replica \
    --db-cluster-identifier "${CLUSTER_NAME}-pg-dr" \
    --region "${DR_REGION}" 2>/dev/null || true
}

switch_dns() {
  echo "[$(date)] Switching DNS from ${PRIMARY_SITE} to ${DR_SITE}..."
  aws route53 change-resource-record-sets \
    --hosted-zone-id "${HOSTED_ZONE_ID}" \
    --change-batch '{
      "Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "'"${PRIMARY_SITE}"'",
          "Type": "CNAME",
          "TTL": 60,
          "ResourceRecords": [{"Value": "'"${DR_SITE}"'"}]
        }
      }]
    }'
}

notify_team() {
  echo "[$(date)] NOTIFICATION: DR failover initiated. Primary: ${PRIMARY_SITE} -> DR: ${DR_SITE}"
}

if ! check_primary_health; then
  echo "[$(date)] PRIMARY SITE IS DOWN! Initiating DR failover..."
  notify_team
  promote_dr_database
  sleep 30
  switch_dns
  echo "[$(date)] DR failover completed. Application should be available at ${DR_SITE}"
  echo "[$(date)] RTO target: < 30 minutes"
else
  echo "[$(date)] Primary site is healthy. No failover needed."
fi