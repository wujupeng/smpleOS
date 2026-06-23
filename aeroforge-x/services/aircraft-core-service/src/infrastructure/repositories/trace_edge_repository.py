from __future__ import annotations

from typing import Optional

from src.infrastructure.repositories.base_repository import AsyncpgRepository
from src.domain.models.trace_edge import TraceEdge


class TraceEdgeRepository(AsyncpgRepository):

    async def create(self, source_node_id: str, target_node_id: str, edge_type: str, properties: Optional[dict] = None) -> TraceEdge:
        import json
        row = await self._fetchrow(
            """
            INSERT INTO dt_trace_edges (source_node_id, target_node_id, edge_type, properties)
            VALUES ($1::uuid, $2::uuid, $3, $4::jsonb)
            RETURNING *
            """,
            source_node_id,
            target_node_id,
            edge_type,
            json.dumps(properties or {}),
        )
        return TraceEdge.from_row(row)

    async def find_outgoing(self, node_id: str) -> list[TraceEdge]:
        rows = await self._fetch(
            "SELECT * FROM dt_trace_edges WHERE source_node_id = $1::uuid ORDER BY created_at",
            node_id,
        )
        return [TraceEdge.from_row(r) for r in rows]

    async def find_incoming(self, node_id: str) -> list[TraceEdge]:
        rows = await self._fetch(
            "SELECT * FROM dt_trace_edges WHERE target_node_id = $1::uuid ORDER BY created_at",
            node_id,
        )
        return [TraceEdge.from_row(r) for r in rows]

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[TraceEdge]:
        rows = await self._fetch(
            "SELECT * FROM dt_trace_edges ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        return [TraceEdge.from_row(r) for r in rows]

    async def delete_all(self) -> int:
        result = await self._execute("DELETE FROM dt_trace_edges")
        return 0