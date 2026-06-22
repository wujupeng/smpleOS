import os
import sys
import logging

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

    logger.info(f"Connecting to Neo4j at {uri}")
    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        driver.verify_connectivity()
        logger.info("Neo4j connectivity verified")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        sys.exit(1)

    constraint_queries = [
        "CREATE CONSTRAINT node_id_unique IF NOT EXISTS FOR (ci:ConfigurationIdentity) REQUIRE ci.node_id IS UNIQUE",
        "CREATE CONSTRAINT aircraft_type_unique IF NOT EXISTS FOR (a:Aircraft) REQUIRE a.aircraft_type IS UNIQUE",
        "CREATE CONSTRAINT block_node_id_unique IF NOT EXISTS FOR (b:Block) REQUIRE b.node_id IS UNIQUE",
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