#!/bin/sh
# AeroForge-X Neo4j Schema Initializer
# Waits for Neo4j to be healthy, then executes Cypher migration scripts

set -e

NEO4J_URI="${NEO4J_URI:-bolt://neo4j:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-aeroforge_neo4j}"
MAX_RETRIES=30
RETRY_INTERVAL=3

echo "[init-neo4j] Waiting for Neo4j at ${NEO4J_URI}..."

retries=0
while [ $retries -lt $MAX_RETRIES ]; do
    if curl -sf "http://neo4j:7474" >/dev/null 2>&1; then
        echo "[init-neo4j] Neo4j is healthy"
        break
    fi
    retries=$((retries + 1))
    echo "[init-neo4j] Retry $retries/$MAX_RETRIES..."
    sleep $RETRY_INTERVAL
done

if [ $retries -eq $MAX_RETRIES ]; then
    echo "[init-neo4j] ERROR: Neo4j not healthy after $MAX_RETRIES retries"
    exit 1
fi

echo "[init-neo4j] Executing v6.0 traceability graph schema..."
cypher-shell -a ${NEO4J_URI} -u ${NEO4J_USER} -p ${NEO4J_PASSWORD} \
    "CREATE CONSTRAINT FOR (req:Requirement) REQUIRE req.node_id IS UNIQUE;" 2>/dev/null || \
    echo "[init-neo4j] Requirement constraint may already exist"

cypher-shell -a ${NEO4J_URI} -u ${NEO4J_USER} -p ${NEO4J_PASSWORD} \
    "CREATE CONSTRAINT FOR (des:DesignElement) REQUIRE des.node_id IS UNIQUE;" 2>/dev/null || \
    echo "[init-neo4j] DesignElement constraint may already exist"

cypher-shell -a ${NEO4J_URI} -u ${NEO4J_USER} -p ${NEO4J_PASSWORD} \
    "CREATE CONSTRAINT FOR (tc:TestCase) REQUIRE tc.node_id IS UNIQUE;" 2>/dev/null || \
    echo "[init-neo4j] TestCase constraint may already exist"

cypher-shell -a ${NEO4J_URI} -u ${NEO4J_USER} -p ${NEO4J_PASSWORD} \
    "CREATE CONSTRAINT FOR (evi:EvidenceItem) REQUIRE evi.node_id IS UNIQUE;" 2>/dev/null || \
    echo "[init-neo4j] EvidenceItem constraint may already exist"

cypher-shell -a ${NEO4J_URI} -u ${NEO4J_USER} -p ${NEO4J_PASSWORD} \
    "CREATE CONSTRAINT FOR (cert:CertificationItem) REQUIRE cert.node_id IS UNIQUE;" 2>/dev/null || \
    echo "[init-neo4j] CertificationItem constraint may already exist"

cypher-shell -a ${NEO4J_URI} -u ${NEO4J_USER} -p ${NEO4J_PASSWORD} \
    "CREATE CONSTRAINT FOR (ml:MaterialLot) REQUIRE ml.lot_id IS UNIQUE;" 2>/dev/null || \
    echo "[init-neo4j] MaterialLot constraint may already exist"

cypher-shell -a ${NEO4J_URI} -u ${NEO4J_USER} -p ${NEO4J_PASSWORD} \
    "CREATE CONSTRAINT FOR (part:InstalledPart) REQUIRE part.part_serial_id IS UNIQUE;" 2>/dev/null || \
    echo "[init-neo4j] InstalledPart constraint may already exist"

cypher-shell -a ${NEO4J_URI} -u ${NEO4J_USER} -p ${NEO4J_PASSWORD} \
    "CREATE CONSTRAINT FOR (ac:Aircraft) REQUIRE ac.tail_number IS UNIQUE;" 2>/dev/null || \
    echo "[init-neo4j] Aircraft constraint may already exist"

echo "[init-neo4j] Neo4j schema initialization complete"