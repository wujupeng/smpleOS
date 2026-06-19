from __future__ import annotations

import logging
from typing import Any

from aeroforge_db.neo4j import get_session as get_neo4j_session

logger = logging.getLogger(__name__)


class MBOMGraphRepository:
    async def save_mbom_tree(self, mbom_id: str, root_item: dict[str, Any]) -> None:
        async with get_neo4j_session() as session:
            await session.run(
                "MERGE (b:BOMItem {itemCode: $code, bomType: 'mbom'}) "
                "SET b.name = $name, b.bomType = $bom_type, b.quantity = $qty, "
                "b.version = $ver, b.station = $station, b.assemblyOrder = $order, "
                "b.isVirtual = $is_virtual, b.mappingStatus = $mapping_status, "
                "b.ebomItemCode = $ebom_code, b.mbomId = $mbom_id",
                code=root_item["item_code"],
                name=root_item.get("name", ""),
                bom_type=root_item.get("bom_type", "mbom"),
                qty=root_item.get("quantity", 1),
                ver=root_item.get("version", "1.0"),
                station=root_item.get("station", ""),
                order=root_item.get("assembly_order", 0),
                is_virtual=root_item.get("is_virtual", False),
                mapping_status=root_item.get("mapping_status", "mapped"),
                ebom_code=root_item.get("ebom_item_code", ""),
                mbom_id=mbom_id,
            )
            for child in root_item.get("children", []):
                await session.run(
                    "MERGE (c:BOMItem {itemCode: $child_code, bomType: 'mbom'}) "
                    "SET c.name = $child_name, c.bomType = $bom_type, c.quantity = $qty, "
                    "c.station = $station, c.assemblyOrder = $order, "
                    "c.isVirtual = $is_virtual, c.mappingStatus = $mapping_status, "
                    "c.ebomItemCode = $ebom_code, c.mbomId = $mbom_id",
                    child_code=child["item_code"],
                    child_name=child.get("name", ""),
                    bom_type=child.get("bom_type", "mbom"),
                    qty=child.get("quantity", 1),
                    station=child.get("station", ""),
                    order=child.get("assembly_order", 0),
                    is_virtual=child.get("is_virtual", False),
                    mapping_status=child.get("mapping_status", "mapped"),
                    ebom_code=child.get("ebom_item_code", ""),
                    mbom_id=mbom_id,
                )
                await session.run(
                    "MATCH (p:BOMItem {itemCode: $parent_code}), (c:BOMItem {itemCode: $child_code}) "
                    "MERGE (p)-[:CONTAINS {quantity: $qty}]->(c)",
                    parent_code=root_item["item_code"],
                    child_code=child["item_code"],
                    qty=child.get("quantity", 1),
                )
                await self.save_mbom_tree(mbom_id, child)

    async def query_mbom_tree(self, mbom_id: str) -> dict[str, Any] | None:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (b:BOMItem {mbomId: $mbom_id, bomType: 'mbom'}) "
                "WHERE NOT (()<-[:CONTAINS]-(b)) "
                "RETURN b.itemCode AS code, b.name AS name, b.quantity AS qty, "
                "b.station AS station, b.assemblyOrder AS assembly_order, "
                "b.isVirtual AS is_virtual, b.mappingStatus AS mapping_status, "
                "b.ebomItemCode AS ebom_item_code "
                "LIMIT 1",
                mbom_id=mbom_id,
            )
            records = await result.data()
            if not records:
                return None
            root = records[0]
            root["item_code"] = root.pop("code")
            root["bom_type"] = "mbom"
            root["children"] = await self._get_children(root["item_code"])
            return root

    async def _get_children(self, parent_code: str) -> list[dict[str, Any]]:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (p:BOMItem {itemCode: $parent_code})-[:CONTAINS]->(c:BOMItem) "
                "RETURN c.itemCode AS code, c.name AS name, c.quantity AS qty, "
                "c.station AS station, c.assemblyOrder AS assembly_order, "
                "c.isVirtual AS is_virtual, c.mappingStatus AS mapping_status, "
                "c.ebomItemCode AS ebom_item_code",
                parent_code=parent_code,
            )
            records = await result.data()
            children: list[dict[str, Any]] = []
            for record in records:
                child = {
                    "item_code": record["code"],
                    "name": record["name"],
                    "quantity": record["qty"],
                    "bom_type": "mbom",
                    "station": record.get("station", ""),
                    "assembly_order": record.get("assembly_order", 0),
                    "is_virtual": record.get("is_virtual", False),
                    "mapping_status": record.get("mapping_status", "mapped"),
                    "ebom_item_code": record.get("ebom_item_code", ""),
                }
                child["children"] = await self._get_children(record["code"])
                children.append(child)
            return children

    async def add_mapping_relation(
        self,
        ebom_item_code: str,
        mbom_item_code: str,
        mapping_type: str = "direct",
    ) -> None:
        async with get_neo4j_session() as session:
            await session.run(
                "MATCH (e:BOMItem {itemCode: $ebom_code, bomType: 'ebom'}) "
                "MATCH (m:BOMItem {itemCode: $mbom_code, bomType: 'mbom'}) "
                "MERGE (e)-[:MAPPED_TO {mappingType: $mapping_type}]->(m)",
                ebom_code=ebom_item_code,
                mbom_code=mbom_item_code,
                mapping_type=mapping_type,
            )
            logger.info("Added MAPPED_TO: %s -> %s (%s)", ebom_item_code, mbom_item_code, mapping_type)

    async def get_unmapped_items(self, mbom_id: str) -> list[dict[str, Any]]:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (b:BOMItem {mbomId: $mbom_id, bomType: 'mbom', mappingStatus: 'unmapped'}) "
                "RETURN b.itemCode AS code, b.name AS name, b.mappingStatus AS status",
                mbom_id=mbom_id,
            )
            records = await result.data()
            return [
                {"item_code": r["code"], "name": r["name"], "mapping_status": r["status"]}
                for r in records
            ]

    async def confirm_mapping(
        self,
        mbom_id: str,
        item_code: str,
        target_station: str,
    ) -> None:
        async with get_neo4j_session() as session:
            await session.run(
                "MATCH (b:BOMItem {itemCode: $code, mbomId: $mbom_id, bomType: 'mbom'}) "
                "SET b.mappingStatus = 'mapped', b.station = $station",
                code=item_code,
                mbom_id=mbom_id,
                station=target_station,
            )
            logger.info("Confirmed mapping: %s -> station %s", item_code, target_station)