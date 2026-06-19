#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== AeroForge-X Development Environment Setup ==="

cd "$PROJECT_DIR"

echo "[1/3] Starting infrastructure services..."
docker compose -f deploy/docker-compose.yml up -d

echo "[2/3] Waiting for services to be healthy..."
sleep 10

echo "[3/3] Running database migrations..."
bash scripts/db-migrate.sh

echo ""
echo "=== Development environment is ready ==="
echo ""
echo "Services:"
echo "  PostgreSQL:  localhost:5432"
echo "  Neo4j:       localhost:7687 (browser: http://localhost:7474)"
echo "  MinIO:       localhost:9000 (console: http://localhost:9001)"
echo "  Redis:       localhost:6379"
echo "  NATS:        localhost:4222 (monitor: http://localhost:8222)"
echo "  Keycloak:    http://localhost:8080"
echo ""
echo "Credentials:"
echo "  PostgreSQL:  aeroforge / aeroforge_dev"
echo "  Neo4j:       neo4j / aeroforge_dev"
echo "  MinIO:       aeroforge_minio / aeroforge_minio_secret"
echo "  Keycloak:    admin / admin"