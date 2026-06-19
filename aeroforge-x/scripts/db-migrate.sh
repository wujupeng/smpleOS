#!/usr/bin/env bash
set -e

echo "=== AeroForge-X Database Migration ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "[1/3] Running PostgreSQL migrations..."
cd libs/aeroforge-db
python -m alembic -c ../../alembic.ini upgrade head
echo "PostgreSQL migrations completed."

echo "[2/3] Running Neo4j initialization..."
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'aeroforge_dev'))
with open('scripts/neo4j-init.cypher', 'r') as f:
    cypher = f.read()
with driver.session() as session:
    for statement in cypher.split(';'):
        stmt = statement.strip()
        if stmt:
            session.run(stmt)
driver.close()
print('Neo4j initialization completed.')
"

echo "[3/3] Running MinIO initialization..."
python scripts/init-minio.py

echo "=== All migrations completed successfully ==="