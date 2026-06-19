from __future__ import annotations

import uuid
from typing import Any

from src.domain.enums import LinkType
from src.domain.value_objects.aircraft_object_link import AircraftObjectLink


class LinkService:

    @staticmethod
    async def create_link(
        source_id: str,
        target_id: str,
        link_type: LinkType,
        propagation_rule: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        pool=None,
    ) -> AircraftObjectLink:
        if source_id == target_id:
            raise ValueError("Self-referencing links are not allowed")

        if link_type in (LinkType.DependsOn, LinkType.ChangePropagatesTo):
            await LinkService._check_circular_dependency(source_id, target_id, link_type, pool)

        link = AircraftObjectLink(
            link_id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            link_type=link_type,
            propagation_rule=propagation_rule or {},
            metadata=metadata or {},
        )

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO aircraft_core.aircraft_object_links (link_id, source_object_id, target_object_id, link_type, propagation_rule, metadata) "
                    "VALUES ($1, $2, $3, $4, $5, $6)",
                    link.link_id, source_id, target_id, link_type.value,
                    propagation_rule or {}, metadata or {},
                )

        return link

    @staticmethod
    async def delete_link(link_id: str, pool) -> bool:
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM aircraft_core.aircraft_object_links WHERE link_id = $1", link_id
            )
            return result == "DELETE 1"

    @staticmethod
    async def get_relationships(
        object_id: str,
        link_type: LinkType | None = None,
        depth: int = 1,
        pool=None,
    ) -> dict[str, Any]:
        async with pool.acquire() as conn:
            if link_type:
                rows = await conn.fetch(
                    "SELECT * FROM aircraft_core.aircraft_object_links WHERE (source_object_id = $1 OR target_object_id = $1) AND link_type = $2",
                    object_id, link_type.value,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM aircraft_core.aircraft_object_links WHERE source_object_id = $1 OR target_object_id = $1",
                    object_id,
                )

        links = [AircraftObjectLink(**dict(r)) for r in rows]
        return {
            "root_object_id": object_id,
            "links": [l.model_dump() for l in links],
            "depth": depth,
            "total_links": len(links),
        }

    @staticmethod
    async def analyze_change_impact(
        object_id: str,
        max_depth: int = 5,
        pool=None,
    ) -> dict[str, Any]:
        affected_objects: list[dict] = []
        propagation_paths: list[list[str]] = []
        visited: set[str] = {object_id}
        queue: list[tuple[str, int, list[str]]] = [(object_id, 0, [object_id])]

        while queue:
            current_id, current_depth, path = queue.pop(0)
            if current_depth >= max_depth:
                continue

            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT target_object_id, link_type, propagation_rule FROM aircraft_core.aircraft_object_links "
                    "WHERE source_object_id = $1 AND link_type = 'change_propagates_to'",
                    current_id,
                )

            for row in rows:
                target_id = row["target_object_id"]
                new_path = path + [target_id]
                propagation_paths.append(new_path)

                if target_id not in visited:
                    visited.add(target_id)
                    affected_objects.append({
                        "object_id": target_id,
                        "depth": current_depth + 1,
                        "propagation_rule": row["propagation_rule"],
                    })
                    queue.append((target_id, current_depth + 1, new_path))

                if len(affected_objects) >= 1000:
                    return {
                        "source_object_id": object_id,
                        "affected_objects": affected_objects,
                        "propagation_paths": propagation_paths,
                        "total_affected": len(affected_objects),
                        "analysis_complete": False,
                    }

        return {
            "source_object_id": object_id,
            "affected_objects": affected_objects,
            "propagation_paths": propagation_paths,
            "total_affected": len(affected_objects),
            "analysis_complete": True,
        }

    @staticmethod
    async def _check_circular_dependency(source_id: str, target_id: str, link_type: LinkType, pool) -> None:
        visited: set[str] = set()
        queue = [target_id]

        while queue:
            current = queue.pop(0)
            if current == source_id:
                raise ValueError(f"Circular dependency detected: adding {source_id}->{target_id} would create a cycle")
            if current in visited:
                continue
            visited.add(current)

            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT target_object_id FROM aircraft_core.aircraft_object_links "
                    "WHERE source_object_id = $1 AND link_type = $2",
                    current, link_type.value,
                )
            for row in rows:
                queue.append(row["target_object_id"])