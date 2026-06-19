from __future__ import annotations

from typing import Any

from src.domain.enums import LinkType


class ObjectQueryService:

    @staticmethod
    async def query_unified_view(object_id: str, pool) -> dict[str, Any] | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM aircraft_core.aircraft_objects WHERE id = $1", object_id
            )
            if row is None:
                return None

            props = await conn.fetch(
                "SELECT pv.*, pd.name as prop_name, pd.property_type, pd.unit "
                "FROM aircraft_core.aircraft_property_values pv "
                "JOIN aircraft_core.property_definitions pd ON pv.property_definition_id = pd.id "
                "WHERE pv.object_id = $1",
                object_id,
            )

            links = await conn.fetch(
                "SELECT * FROM aircraft_core.aircraft_object_links WHERE source_object_id = $1 OR target_object_id = $1",
                object_id,
            )

        result = dict(row)
        result["properties"] = [dict(p) for p in props]
        result["links"] = [dict(l) for l in links]
        return result

    @staticmethod
    async def query_by_property(
        property_type: str | None = None,
        value_range: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
        pool=None,
    ) -> dict[str, Any]:
        conditions = []
        params = []
        param_idx = 0

        if property_type:
            param_idx += 1
            conditions.append(f"pd.property_type = ${param_idx}")
            params.append(property_type)

        if value_range:
            if "min" in value_range:
                param_idx += 1
                conditions.append(f"(pv.value)::float >= ${param_idx}")
                params.append(value_range["min"])
            if "max" in value_range:
                param_idx += 1
                conditions.append(f"(pv.value)::float <= ${param_idx}")
                params.append(value_range["max"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT DISTINCT o.* FROM aircraft_core.aircraft_objects o "
                f"JOIN aircraft_core.aircraft_property_values pv ON o.id = pv.object_id "
                f"JOIN aircraft_core.property_definitions pd ON pv.property_definition_id = pd.id "
                f"WHERE {where_clause} ORDER BY o.updated_at DESC LIMIT {limit} OFFSET {offset}",
                *params,
            )
            total = await conn.fetchval(
                f"SELECT COUNT(DISTINCT o.id) FROM aircraft_core.aircraft_objects o "
                f"JOIN aircraft_core.aircraft_property_values pv ON o.id = pv.object_id "
                f"JOIN aircraft_core.property_definitions pd ON pv.property_definition_id = pd.id "
                f"WHERE {where_clause}",
                *params,
            )

        return {
            "objects": [dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    async def traverse_relationships(
        object_id: str,
        depth: int = 3,
        link_types: list[str] | None = None,
        pool=None,
    ) -> dict[str, Any]:
        from src.domain.services.link_service import LinkService
        return await LinkService.get_relationships(object_id, link_types=link_types, depth=depth, pool=pool)

    @staticmethod
    async def analyze_change_impact(
        object_id: str,
        max_depth: int = 5,
        pool=None,
    ) -> dict[str, Any]:
        from src.domain.services.link_service import LinkService
        return await LinkService.analyze_change_impact(object_id, max_depth=max_depth, pool=pool)