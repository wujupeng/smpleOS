from __future__ import annotations

import logging

from src.infrastructure.database import get_neo4j_driver

logger = logging.getLogger(__name__)


class Neo4jGraphClient:
    async def create_configuration_identity(
        self,
        node_id: str,
        block_name: str,
        aircraft_type: str,
        configuration_type: str = "Block",
        version: int = 1,
    ) -> bool:
        driver = await get_neo4j_driver()
        if driver is None:
            return False
        try:
            async with driver.session() as session:
                await session.run(
                    "MERGE (a:Aircraft {aircraft_type: $aircraft_type}) "
                    "MERGE (b:Block {node_id: $node_id}) "
                    "SET b.block_name = $block_name, b.aircraft_type = $aircraft_type, b.version = $version "
                    "MERGE (a)-[:HAS_BLOCK]->(b) "
                    "MERGE (ci:ConfigurationIdentity {node_id: $node_id}) "
                    "SET ci.configuration_type = $configuration_type, ci.version = $version "
                    "MERGE (b)-[:HAS_IDENTITY]->(ci)",
                    node_id=node_id,
                    block_name=block_name,
                    aircraft_type=aircraft_type,
                    configuration_type=configuration_type,
                    version=version,
                )
                logger.info(f"Neo4j: created identity for {node_id}")
                return True
        except Exception as e:
            logger.warning(f"Neo4j create_configuration_identity failed: {e}")
            return False

    async def create_sn_node(self, sn_node_id: str, tail_number: str, block_node_id: str) -> bool:
        driver = await get_neo4j_driver()
        if driver is None:
            return False
        try:
            async with driver.session() as session:
                await session.run(
                    "MERGE (sn:SN {node_id: $sn_node_id}) "
                    "SET sn.tail_number = $tail_number "
                    "MATCH (b:Block {node_id: $block_node_id}) "
                    "MERGE (b)-[:HAS_SN]->(sn)",
                    sn_node_id=sn_node_id,
                    tail_number=tail_number,
                    block_node_id=block_node_id,
                )
                logger.info(f"Neo4j: created SN node {sn_node_id}")
                return True
        except Exception as e:
            logger.warning(f"Neo4j create_sn_node failed: {e}")
            return False

    async def query_identity_graph(self, aircraft_type: str) -> dict:
        driver = await get_neo4j_driver()
        if driver is None:
            return {"aircraft_type": aircraft_type, "blocks": [], "neo4j_available": False}
        try:
            async with driver.session() as session:
                result = await session.run(
                    "MATCH (a:Aircraft {aircraft_type: $aircraft_type})-[:HAS_BLOCK]->(b:Block) "
                    "OPTIONAL MATCH (b)-[:HAS_SN]->(sn:SN) "
                    "RETURN b.node_id AS block_id, b.block_name AS block_name, b.version AS version, "
                    "collect(sn.node_id) AS sn_ids, collect(sn.tail_number) AS tail_numbers",
                    aircraft_type=aircraft_type,
                )
                blocks = []
                async for record in result:
                    sn_list = []
                    for sid, tn in zip(record["sn_ids"], record["tail_numbers"]):
                        if sid:
                            sn_list.append({"sn_node_id": sid, "tail_number": tn})
                    blocks.append({
                        "block_id": record["block_id"],
                        "block_name": record["block_name"],
                        "version": record["version"],
                        "serial_numbers": sn_list,
                    })
                return {"aircraft_type": aircraft_type, "blocks": blocks, "neo4j_available": True}
        except Exception as e:
            logger.warning(f"Neo4j query_identity_graph failed: {e}")
            return {"aircraft_type": aircraft_type, "blocks": [], "neo4j_available": False, "error": str(e)}


graph_client = Neo4jGraphClient()