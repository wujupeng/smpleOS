import os
import sys
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    try:
        from neo4j import GraphDatabase
    except ImportError:
        logger.error("neo4j driver not installed, installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "neo4j>=5.0.0"])
        from neo4j import GraphDatabase

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "aeroforge_neo4j")

    max_retries = 12
    retry_interval = 5
    driver = None

    for attempt in range(1, max_retries + 1):
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {uri} (attempt {attempt}/{max_retries})")
            break
        except Exception as e:
            logger.warning(f"Neo4j connection attempt {attempt}/{max_retries} failed: {e}")
            if driver:
                driver.close()
                driver = None
            if attempt == max_retries:
                logger.error(f"Failed to connect to Neo4j after {max_retries} attempts")
                sys.exit(1)
            time.sleep(retry_interval)

    constraint_queries = [
        "CREATE CONSTRAINT identity_id_unique IF NOT EXISTS FOR (ci:ConfigurationIdentity) REQUIRE ci.identity_id IS UNIQUE",
        "CREATE CONSTRAINT material_lot_domain_id_unique IF NOT EXISTS FOR (m:MaterialLot) REQUIRE m.domain_id IS UNIQUE",
        "CREATE CONSTRAINT ndt_record_domain_id_unique IF NOT EXISTS FOR (n:NDTRecord) REQUIRE n.domain_id IS UNIQUE",
        "CREATE CONSTRAINT car_domain_id_unique IF NOT EXISTS FOR (c:CAR) REQUIRE c.domain_id IS UNIQUE",
        "CREATE CONSTRAINT evidence_domain_id_unique IF NOT EXISTS FOR (e:Evidence) REQUIRE e.domain_id IS UNIQUE",
        "CREATE CONSTRAINT compliance_req_domain_id_unique IF NOT EXISTS FOR (cr:ComplianceRequirement) REQUIRE cr.domain_id IS UNIQUE",
        "CREATE CONSTRAINT block_node_id_unique IF NOT EXISTS FOR (b:Block) REQUIRE b.node_id IS UNIQUE",
        "CREATE CONSTRAINT aircraft_type_unique IF NOT EXISTS FOR (a:Aircraft) REQUIRE a.aircraft_type IS UNIQUE",
        "CREATE CONSTRAINT sn_node_id_unique IF NOT EXISTS FOR (sn:SN) REQUIRE sn.node_id IS UNIQUE",
        "CREATE CONSTRAINT requirement_node_id_unique IF NOT EXISTS FOR (r:Requirement) REQUIRE r.node_id IS UNIQUE",
        "CREATE CONSTRAINT design_element_node_id_unique IF NOT EXISTS FOR (de:DesignElement) REQUIRE de.node_id IS UNIQUE",
    ]

    with driver.session() as session:
        for q in constraint_queries:
            try:
                session.run(q)
                label = q.split("FOR (")[1].split(")")[0].split(":")[1]
                logger.info(f"Constraint for {label} ensured")
            except Exception as e:
                if "already exists" in str(e).lower():
                    label = q.split("FOR (")[1].split(")")[0].split(":")[1]
                    logger.info(f"Constraint already exists: {label}, skipping")
                else:
                    logger.warning(f"Constraint issue: {e}")

        seed_queries = [
            "MERGE (a:Aircraft {aircraft_type: 'B737'})",
            "MERGE (a:Aircraft {aircraft_type: 'B737'}) MERGE (b:Block {node_id: 'B737-WING-001', block_name: 'Wing', aircraft_type: 'B737'}) MERGE (a)-[:HAS_BLOCK]->(b)",
            "MERGE (a:Aircraft {aircraft_type: 'B737'}) MERGE (b:Block {node_id: 'B737-FUSE-001', block_name: 'Fuselage', aircraft_type: 'B737'}) MERGE (a)-[:HAS_BLOCK]->(b)",
            "MERGE (a:Aircraft {aircraft_type: 'B737'}) MERGE (b:Block {node_id: 'B737-ENG-001', block_name: 'Engine', aircraft_type: 'B737'}) MERGE (a)-[:HAS_BLOCK]->(b)",
        ]

        for q in seed_queries:
            try:
                session.run(q)
            except Exception as e:
                logger.warning(f"Seed data issue: {e}")

        result = session.run(
            "MATCH (a:Aircraft {aircraft_type: 'B737'})-[:HAS_BLOCK]->(b:Block) RETURN count(b) AS cnt"
        )
        cnt = result.single()["cnt"]
        logger.info(f"B737 seed data: {cnt} blocks created")

    driver.close()
    logger.info("Neo4j schema initialization complete")


if __name__ == "__main__":
    main()
