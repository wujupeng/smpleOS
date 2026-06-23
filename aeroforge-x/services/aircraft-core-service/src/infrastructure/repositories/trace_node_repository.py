from __future__ import annotations

from typing import Optional

from src.infrastructure.repositories.base_repository import AsyncpgRepository
from src.domain.models.trace_node import TraceNode


class TraceNodeRepository(AsyncpgRepository):

    async def create(self, identity_id: Optional[str], node_type: str, label: str, properties: Optional[dict] = None) -> TraceNode:
        import json
        row = await self._fetchrow(
            """
            INSERT INTO dt_trace_nodes (identity_id, node_type, label, properties)
            VALUES ($1::uuid, $2, $3, $4::jsonb)
            RETURNING *
            """,
            identity_id,
            node_type,
            label,
            json.dumps(properties or {}),
        )
        return TraceNode.from_row(row)

    async def find_by_id(self, node_id: str) -> Optional[TraceNode]:
        row = await self._fetchrow(
            "SELECT * FROM dt_trace_nodes WHERE node_id = $1::uuid",
            node_id,
        )
        return TraceNode.from_row(row) if row else None

    async def find_by_identity(self, identity_id: str) -> Optional[TraceNode]:
        row = await self._fetchrow(
            "SELECT * FROM dt_trace_nodes WHERE identity_id = $1::uuid",
            identity_id,
        )
        return TraceNode.from_row(row) if row else None

    async def find_by_type(self, node_type: str, limit: int = 100, offset: int = 0) -> list[TraceNode]:
        rows = await self._fetch(
            "SELECT * FROM dt_trace_nodes WHERE node_type = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            node_type,
            limit,
            offset,
        )
        return [TraceNode.from_row(r) for r in rows]

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[TraceNode]:
        rows = await self._fetch(
            "SELECT * FROM dt_trace_nodes ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        return [TraceNode.from_row(r) for r in rows]

    async def update_properties(self, node_id: str, properties: dict) -> Optional[TraceNode]:
        import json
        row = await self._fetchrow(
            "UPDATE dt_trace_nodes SET properties = $1::jsonb WHERE node_id = $2::uuid RETURNING *",
            json.dumps(properties),
            node_id,
        )
        return TraceNode.from_row(row) if row else None

    async def delete_all(self) -> int:
        result = await self._execute("DELETE FROM dt_trace_edges; DELETE FROM dt_trace_nodes")
        return 0