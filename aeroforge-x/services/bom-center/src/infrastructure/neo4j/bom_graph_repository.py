from __future__ import annotations

from typing import Any

from aeroforge_db.neo4j import get_session as get_neo4j_session


class BOMGraphRepository:
    async def save_bom_tree(self, ebom_id: str, root_item: dict[str, Any]) -> None:
        async with get_neo4j_session() as session:
            await session.run(
                "MERGE (b:BOMItem {itemCode: $code}) SET b.name = $name, b.bomType = $bom_type, b.quantity = $qty, b.version = $ver",
                code=root_item["item_code"],
                name=root_item.get("name", ""),
                bom_type=root_item.get("bom_type", "ebom"),
                qty=root_item.get("quantity", 1),
                ver=root_item.get("version", "1.0"),
            )
            for child in root_item.get("children", []):
                await session.run(
                    "MERGE (c:BOMItem {itemCode: $child_code}) SET c.name = $child_name, c.bomType = $bom_type, c.quantity = $qty",
                    child_code=child["item_code"],
                    child_name=child.get("name", ""),
                    bom_type=child.get("bom_type", "ebom"),
                    qty=child.get("quantity", 1),
                )
                await session.run(
                    "MATCH (p:BOMItem {itemCode: $parent_code}), (c:BOMItem {itemCode: $child_code}) "
                    "MERGE (p)-[:CONTAINS {quantity: $qty}]->(c)",
                    parent_code=root_item["item_code"],
                    child_code=child["item_code"],
                    qty=child.get("quantity", 1),
                )
                await self.save_bom_tree(ebom_id, child)

    async def query_bom_tree(self, root_item_code: str) -> dict[str, Any] | None:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (b:BOMItem {itemCode: $code}) RETURN b",
                code=root_item_code,
            )
            records = await result.data()
            if not records:
                return None
            root = dict(records[0]["b"])
            children = await self._get_children(root_item_code)
            root["children"] = children
            return root

    async def _get_children(self, parent_code: str) -> list[dict[str, Any]]:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (p:BOMItem {itemCode: $parent_code})-[:CONTAINS]->(c:BOMItem) RETURN c.itemCode AS code, c.name AS name, c.quantity AS qty",
                parent_code=parent_code,
            )
            records = await result.data()
            children: list[dict[str, Any]] = []
            for record in records:
                child = {"item_code": record["code"], "name": record["name"], "quantity": record["qty"]}
                child["children"] = await self._get_children(record["code"])
                children.append(child)
            return children