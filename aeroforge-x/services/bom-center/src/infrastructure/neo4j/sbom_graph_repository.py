from __future__ import annotations

import logging
from typing import Any

from aeroforge_db.neo4j import get_session as get_neo4j_session

logger = logging.getLogger(__name__)


class SBOMGraphRepository:
    async def save_sbom_tree(self, sbom_id: str, root_item: dict[str, Any]) -> None:
        async with get_neo4j_session() as session:
            await session.run(
                "MERGE (b:BOMItem {itemCode: $code, bomType: 'sbom'}) "
                "SET b.name = $name, b.bomType = $bom_type, b.quantity = $qty, "
                "b.version = $ver, b.partType = $part_type, "
                "b.spareCategory = $spare_cat, b.replacementCycleFh = $cycle, "
                "b.maintenanceStrategy = $strategy, b.procurementLeadTime = $lead_time, "
                "b.sbomId = $sbom_id",
                code=root_item["item_code"],
                name=root_item.get("name", ""),
                bom_type="sbom",
                qty=root_item.get("quantity", 1),
                ver=root_item.get("version", "1.0"),
                part_type=root_item.get("part_type", "part"),
                spare_cat=root_item.get("attributes", {}).get("spare_part_category", ""),
                cycle=root_item.get("attributes", {}).get("replacement_cycle_fh", 0),
                strategy=root_item.get("attributes", {}).get("maintenance_strategy", ""),
                lead_time=root_item.get("attributes", {}).get("procurement_lead_time_days", 0),
                sbom_id=sbom_id,
            )
            for child in root_item.get("children", []):
                await session.run(
                    "MERGE (c:BOMItem {itemCode: $child_code, bomType: 'sbom'}) "
                    "SET c.name = $child_name, c.bomType = $bom_type, c.quantity = $qty, "
                    "c.partType = $part_type, c.sbomId = $sbom_id",
                    child_code=child["item_code"],
                    child_name=child.get("name", ""),
                    bom_type="sbom",
                    qty=child.get("quantity", 1),
                    part_type=child.get("part_type", "part"),
                    sbom_id=sbom_id,
                )
                await session.run(
                    "MATCH (p:BOMItem {itemCode: $parent_code}), (c:BOMItem {itemCode: $child_code}) "
                    "MERGE (p)-[:CONTAINS {quantity: $qty}]->(c)",
                    parent_code=root_item["item_code"],
                    child_code=child["item_code"],
                    qty=child.get("quantity", 1),
                )
                await self.save_sbom_tree(sbom_id, child)

    async def query_sbom_tree(self, sbom_id: str) -> dict[str, Any] | None:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (b:BOMItem {sbomId: $sbom_id, bomType: 'sbom'}) "
                "WHERE NOT (()<-[:CONTAINS]-(b)) "
                "RETURN b.itemCode AS code, b.name AS name, b.quantity AS qty, "
                "b.partType AS part_type, b.spareCategory AS spare_cat, "
                "b.replacementCycleFh AS cycle, b.maintenanceStrategy AS strategy, "
                "b.procurementLeadTime AS lead_time "
                "LIMIT 1",
                sbom_id=sbom_id,
            )
            records = await result.data()
            if not records:
                return None
            root = records[0]
            root["item_code"] = root.pop("code")
            root["bom_type"] = "sbom"
            root["attributes"] = {
                "spare_part_category": root.pop("spare_cat", ""),
                "replacement_cycle_fh": root.pop("cycle", 0),
                "maintenance_strategy": root.pop("strategy", ""),
                "procurement_lead_time_days": root.pop("lead_time", 0),
            }
            root["children"] = await self._get_children(root["item_code"])
            return root

    async def _get_children(self, parent_code: str) -> list[dict[str, Any]]:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (p:BOMItem {itemCode: $parent_code})-[:CONTAINS]->(c:BOMItem) "
                "RETURN c.itemCode AS code, c.name AS name, c.quantity AS qty, "
                "c.partType AS part_type, c.spareCategory AS spare_cat, "
                "c.replacementCycleFh AS cycle, c.maintenanceStrategy AS strategy, "
                "c.procurementLeadTime AS lead_time",
                parent_code=parent_code,
            )
            records = await result.data()
            children: list[dict[str, Any]] = []
            for record in records:
                child = {
                    "item_code": record["code"],
                    "name": record["name"],
                    "quantity": record["qty"],
                    "bom_type": "sbom",
                    "part_type": record.get("part_type", "part"),
                    "attributes": {
                        "spare_part_category": record.get("spare_cat", ""),
                        "replacement_cycle_fh": record.get("cycle", 0),
                        "maintenance_strategy": record.get("strategy", ""),
                        "procurement_lead_time_days": record.get("lead_time", 0),
                    },
                }
                child["children"] = await self._get_children(record["code"])
                children.append(child)
            return children

    async def add_mapping_relation(
        self,
        ebom_item_code: str,
        sbom_item_code: str,
        mapping_type: str = "direct",
    ) -> None:
        async with get_neo4j_session() as session:
            await session.run(
                "MATCH (e:BOMItem {itemCode: $ebom_code, bomType: 'ebom'}) "
                "MATCH (s:BOMItem {itemCode: $sbom_code, bomType: 'sbom'}) "
                "MERGE (e)-[:MAPPED_TO {mappingType: $mapping_type}]->(s)",
                ebom_code=ebom_item_code,
                sbom_code=sbom_item_code,
                mapping_type=mapping_type,
            )
            logger.info("Added MAPPED_TO: %s -> %s (%s)", ebom_item_code, sbom_item_code, mapping_type)