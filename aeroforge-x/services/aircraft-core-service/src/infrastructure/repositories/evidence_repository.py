from __future__ import annotations

from typing import Optional

from src.infrastructure.repositories.base_repository import AsyncpgRepository
from src.domain.models.evidence import Evidence


class EvidenceRepository(AsyncpgRepository):

    async def create(
        self,
        requirement_id: str,
        file_id: str,
        file_name: str,
        bucket: str,
        content_type: str,
        file_size: int,
    ) -> Evidence:
        row = await self._fetchrow(
            """
            INSERT INTO dt_evidences
                (requirement_id, file_id, file_name, bucket, content_type, file_size)
            VALUES ($1, $2::uuid, $3, $4, $5, $6)
            RETURNING *
            """,
            requirement_id,
            file_id,
            file_name,
            bucket,
            content_type,
            file_size,
        )
        return Evidence.from_row(row)

    async def find_by_id(self, evidence_id: str) -> Optional[Evidence]:
        row = await self._fetchrow(
            "SELECT * FROM dt_evidences WHERE evidence_id = $1::uuid",
            evidence_id,
        )
        return Evidence.from_row(row) if row else None

    async def find_by_requirement(self, requirement_id: str) -> list[Evidence]:
        rows = await self._fetch(
            "SELECT * FROM dt_evidences WHERE requirement_id = $1 ORDER BY upload_timestamp DESC",
            requirement_id,
        )
        return [Evidence.from_row(r) for r in rows]