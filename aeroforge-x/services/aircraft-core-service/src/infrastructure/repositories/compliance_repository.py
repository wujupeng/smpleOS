from __future__ import annotations

from typing import Optional

from src.infrastructure.repositories.base_repository import AsyncpgRepository
from src.domain.models.compliance_requirement import ComplianceRequirement
from src.domain.models.evidence import Evidence


class ComplianceRepository(AsyncpgRepository):

    async def find_or_create(
        self,
        requirement_id: str,
        regulation: str,
        description: str,
    ) -> ComplianceRequirement:
        row = await self._fetchrow(
            "SELECT * FROM dt_compliance_requirements WHERE requirement_id = $1",
            requirement_id,
        )
        if row:
            return ComplianceRequirement.from_row(row)

        row = await self._fetchrow(
            """
            INSERT INTO dt_compliance_requirements
                (requirement_id, regulation, description, compliance_status)
            VALUES ($1, $2, $3, 'pending')
            ON CONFLICT (requirement_id) DO UPDATE SET requirement_id = EXCLUDED.requirement_id
            RETURNING *
            """,
            requirement_id,
            regulation,
            description,
        )
        return ComplianceRequirement.from_row(row)

    async def find_by_id(self, requirement_id: str) -> Optional[ComplianceRequirement]:
        row = await self._fetchrow(
            "SELECT * FROM dt_compliance_requirements WHERE requirement_id = $1",
            requirement_id,
        )
        return ComplianceRequirement.from_row(row) if row else None

    async def update_compliance_status(
        self,
        requirement_id: str,
        compliance_status: str,
        responsible_person: Optional[str] = None,
    ) -> Optional[ComplianceRequirement]:
        row = await self._fetchrow(
            """
            UPDATE dt_compliance_requirements
            SET compliance_status = $2, updated_at = NOW()
            WHERE requirement_id = $1
            RETURNING *
            """,
            requirement_id,
            compliance_status,
        )
        if row and responsible_person:
            row2 = await self._fetchrow(
                """
                UPDATE dt_compliance_requirements
                SET responsible_person = $2, updated_at = NOW()
                WHERE requirement_id = $1
                RETURNING *
                """,
                requirement_id,
                responsible_person,
            )
            return ComplianceRequirement.from_row(row2) if row2 else None
        return ComplianceRequirement.from_row(row) if row else None

    async def find_evidences(self, requirement_id: str) -> list[Evidence]:
        rows = await self._fetch(
            "SELECT * FROM dt_evidences WHERE requirement_id = $1 ORDER BY upload_timestamp DESC",
            requirement_id,
        )
        return [Evidence.from_row(r) for r in rows]

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[ComplianceRequirement]:
        rows = await self._fetch(
            "SELECT * FROM dt_compliance_requirements ORDER BY updated_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        return [ComplianceRequirement.from_row(r) for r in rows]