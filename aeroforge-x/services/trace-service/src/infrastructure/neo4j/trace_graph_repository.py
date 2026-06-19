from __future__ import annotations

from typing import Any

from aeroforge_db.neo4j import get_session as get_neo4j_session


class TraceGraphRepository:
    async def add_trace_link(
        self,
        from_label: str,
        from_props: dict[str, Any],
        relation: str,
        to_label: str,
        to_props: dict[str, Any],
        relation_props: dict[str, Any] | None = None,
    ) -> None:
        async with get_neo4j_session() as session:
            from_set = ", ".join(f"a.{k} = ${k}" for k in from_props)
            to_set = ", ".join(f"b.{k} = ${k}" for k in to_props)
            await session.run(
                f"MERGE (a:{from_label} {{code: $from_code}}) SET {from_set} "
                f"MERGE (b:{to_label} {{code: $to_code}}) SET {to_set} "
                f"MERGE (a)-[r:{relation}]->(b)",
                {**from_props, **to_props, "from_code": from_props.get("code", ""), "to_code": to_props.get("code", "")},
            )

    async def find_trace_path(self, serial_number: str) -> list[dict[str, Any]]:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH path = (s:Supplier)-[*..6]->(a:Aircraft {serialNumber: $sn}) "
                "RETURN [n in nodes(path) | {label: labels(n)[0], properties: properties(n)}] AS nodes, "
                "[r in relationships(path) | type(r)] AS relations",
                sn=serial_number,
            )
            records = await result.data()
            return records

    async def find_batch_forward_trace(self, batch_number: str) -> list[dict[str, Any]]:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (b:Batch {batchNumber: $bn})-[*..6]->(target) "
                "RETURN DISTINCT {label: labels(target)[0], properties: properties(target)} AS target",
                bn=batch_number,
            )
            records = await result.data()
            return records

    async def find_batch_reverse_trace(self, aircraft_code: str) -> list[dict[str, Any]]:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH path = (s:Supplier)-[*..6]->(a:Aircraft {aircraftCode: $ac}) "
                "RETURN [n in nodes(path) | {label: labels(n)[0], properties: properties(n)}] AS nodes",
                ac=aircraft_code,
            )
            records = await result.data()
            return records

    async def detect_broken_links(self, serial_number: str) -> list[dict[str, Any]]:
        async with get_neo4j_session() as session:
            result = await session.run(
                "MATCH (p:Part {serialNumber: $sn}) "
                "WHERE NOT (p)<-[:SUPPLIED]-(:Supplier) OR NOT (p)-[:INSTALLED_IN]->(:Aircraft) "
                "RETURN p.serialNumber AS sn, labels(p) AS labels",
                sn=serial_number,
            )
            records = await result.data()
            return records