#!/bin/bash
# AeroForge-X Database Migration Runner
# Executes all SQL migrations against PostgreSQL/TimescaleDB in order
# Usage: ./run_migrations.sh [--pg-host HOST] [--pg-port PORT] [--pg-user USER] [--pg-db DB]

set -e

PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-postgres}"
PG_DB="${PG_DB:-aeroforge}"
PG_PASSWORD="${PG_PASSWORD:-aeroforge}"

TS_HOST="${TS_HOST:-localhost}"
TS_PORT="${TS_PORT:-5433}"
TS_USER="${TS_USER:-postgres}"
TS_DB="${TS_DB:-aeroforge_ts}"
TS_PASSWORD="${TS_PASSWORD:-aeroforge_ts}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MIGRATIONS_DIR="$(dirname "$SCRIPT_DIR")/migrations"
REPORT_FILE="$(dirname "$SCRIPT_DIR")/migration_report.md"

export PGPASSWORD="${PG_PASSWORD}"

run_sql() {
    local db_host="$1"
    local db_port="$2"
    local db_user="$3"
    local db_name="$4"
    local sql_file="$5"
    local label="$6"

    echo "" >> "$REPORT_FILE"
    echo "### ${label}" >> "$REPORT_FILE"
    echo "- **File**: \`${sql_file##*/}\`" >> "$REPORT_FILE"
    echo -n "- **Status**: " >> "$REPORT_FILE"

    if psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -f "$sql_file" >> /tmp/migration_output.log 2>&1; then
        echo "SUCCESS" >> "$REPORT_FILE"
        echo "[OK] ${label}"
    else
        echo "FAILED (see /tmp/migration_output.log)" >> "$REPORT_FILE"
        echo "[FAIL] ${label}"
        return 1
    fi
}

echo "# AeroForge-X Migration Report" > "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- **Date**: $(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$REPORT_FILE"
echo "- **PostgreSQL**: ${PG_HOST}:${PG_PORT}/${PG_DB}" >> "$REPORT_FILE"
echo "- **TimescaleDB**: ${TS_HOST}:${TS_PORT}/${TS_DB}" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"

echo "=== AeroForge-X Migration Runner ==="
echo "PostgreSQL: ${PG_HOST}:${PG_PORT}/${PG_DB}"
echo "TimescaleDB: ${TS_HOST}:${TS_PORT}/${TS_DB}"
echo ""

echo "## Phase 1: v2.0 Base Tables (PostgreSQL)" >> "$REPORT_FILE"
echo "[Phase 1] v2.0 Base Tables (PostgreSQL)"
for f in "${MIGRATIONS_DIR}/v2_0/"001_aircraft_core_tables.sql \
         "${MIGRATIONS_DIR}/v2_0/"002_workflow_engine_tables.sql \
         "${MIGRATIONS_DIR}/v2_0/"003_physics_twin_tables.sql; do
    if [ -f "$f" ]; then
        run_sql "$PG_HOST" "$PG_PORT" "$PG_USER" "$PG_DB" "$f" "v2.0: $(basename "$f")" || true
    else
        echo "[SKIP] $f not found"
    fi
done

echo "" >> "$REPORT_FILE"
echo "## Phase 2: v2.0 TimescaleDB Tables" >> "$REPORT_FILE"
echo "[Phase 2] v2.0 TimescaleDB Tables"
export PGPASSWORD="${TS_PASSWORD}"
for f in "${MIGRATIONS_DIR}/v2_0/"004_timescale_twin_tables.sql; do
    if [ -f "$f" ]; then
        run_sql "$TS_HOST" "$TS_PORT" "$TS_USER" "$TS_DB" "$f" "v2.0 TimescaleDB: $(basename "$f")" || true
    fi
done
export PGPASSWORD="${PG_PASSWORD}"

echo "" >> "$REPORT_FILE"
echo "## Phase 3: v6.0 Tables (PostgreSQL)" >> "$REPORT_FILE"
echo "[Phase 3] v6.0 Tables (PostgreSQL)"
for f in "${MIGRATIONS_DIR}/v6_0/"001_physics_twin_v6_tables.sql \
         "${MIGRATIONS_DIR}/v6_0/"002_aircraft_core_v6_tables.sql; do
    if [ -f "$f" ]; then
        run_sql "$PG_HOST" "$PG_PORT" "$PG_USER" "$PG_DB" "$f" "v6.0: $(basename "$f")" || true
    fi
done

echo "" >> "$REPORT_FILE"
echo "## Phase 4: v6.0 TimescaleDB Tables" >> "$REPORT_FILE"
echo "[Phase 4] v6.0 TimescaleDB Tables"
export PGPASSWORD="${TS_PASSWORD}"
for f in "${MIGRATIONS_DIR}/v6_0/"003_timescale_v6_tables.sql; do
    if [ -f "$f" ]; then
        run_sql "$TS_HOST" "$TS_PORT" "$TS_USER" "$TS_DB" "$f" "v6.0 TimescaleDB: $(basename "$f")" || true
    fi
done
export PGPASSWORD="${PG_PASSWORD}"

echo "" >> "$REPORT_FILE"
echo "## Phase 5: V6.1 Tables (PostgreSQL)" >> "$REPORT_FILE"
echo "[Phase 5] V6.1 Tables (PostgreSQL)"
for f in "${MIGRATIONS_DIR}/v6_1/"004_v61_physics_twin_tables.sql \
         "${MIGRATIONS_DIR}/v6_1/"005_v61_aircraft_core_tables.sql; do
    if [ -f "$f" ]; then
        run_sql "$PG_HOST" "$PG_PORT" "$PG_USER" "$PG_DB" "$f" "V6.1: $(basename "$f")" || true
    fi
done

echo "" >> "$REPORT_FILE"
echo "## Phase 6: v6.2 Configuration UUID Tables (PostgreSQL)" >> "$REPORT_FILE"
echo "[Phase 6] v6.2 Configuration UUID Tables (PostgreSQL)"
for f in "${MIGRATIONS_DIR}/v6_2/"006_configuration_uuid_tables.sql; do
    if [ -f "$f" ]; then
        run_sql "$PG_HOST" "$PG_PORT" "$PG_USER" "$PG_DB" "$f" "v6.2: $(basename "$f")" || true
    fi
done

echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "## Notes" >> "$REPORT_FILE"
echo "- Neo4j schema is initialized by init-neo4j container in docker-compose" >> "$REPORT_FILE"
echo "- NATS streams are initialized by init-nats container in docker-compose" >> "$REPORT_FILE"
echo "- MinIO buckets are initialized by init-minio container in docker-compose" >> "$REPORT_FILE"

echo ""
echo "=== Migration complete. Report: ${REPORT_FILE} ==="