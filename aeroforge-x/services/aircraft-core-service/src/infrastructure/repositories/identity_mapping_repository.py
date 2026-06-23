from __future__ import annotations

from typing import Optional

from src.infrastructure.repositories.base_repository import AsyncpgRepository
from src.domain.models.identity_mapping import IdentityMapping


class IdentityMappingRepository(AsyncpgRepository):

    async def upsert(self, identity_id: str, domain: str, domain_id: str) -> IdentityMapping:
        row = await self._fetchrow(
            """
            INSERT INTO dt_identity_mappings (identity_id, domain, domain_id)
            VALUES ($1::uuid, $2, $3)
            ON CONFLICT (domain, domain_id) DO UPDATE SET identity_id = EXCLUDED.identity_id
            RETURNING *
            """,
            identity_id,
            domain,
            domain_id,
        )
        return IdentityMapping.from_row(row)

    async def find_by_identity(self, identity_id: str) -> list[IdentityMapping]:
        rows = await self._fetch(
            "SELECT * FROM dt_identity_mappings WHERE identity_id = $1::uuid ORDER BY created_at",
            identity_id,
        )
        return [IdentityMapping.from_row(r) for r in rows]

    async def find_by_domain(self, domain: str, domain_id: str) -> Optional[IdentityMapping]:
        row = await self._fetchrow(
            "SELECT * FROM dt_identity_mappings WHERE domain = $1 AND domain_id = $2",
            domain,
            domain_id,
        )
        return IdentityMapping.from_row(row) if row else None