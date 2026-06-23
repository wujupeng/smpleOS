from __future__ import annotations

from typing import Optional

from src.infrastructure.repositories.base_repository import AsyncpgRepository
from src.domain.models.configuration_identity import ConfigurationIdentity


class ConfigurationIdentityRepository(AsyncpgRepository):

    async def create(self, label: str, node_type: str) -> ConfigurationIdentity:
        row = await self._fetchrow(
            """
            INSERT INTO dt_configuration_identities (label, node_type)
            VALUES ($1, $2)
            RETURNING *
            """,
            label,
            node_type,
        )
        return ConfigurationIdentity.from_row(row)

    async def find_by_id(self, identity_id: str) -> Optional[ConfigurationIdentity]:
        row = await self._fetchrow(
            "SELECT * FROM dt_configuration_identities WHERE identity_id = $1::uuid",
            identity_id,
        )
        return ConfigurationIdentity.from_row(row) if row else None

    async def find_by_domain(self, domain: str, domain_id: str) -> Optional[ConfigurationIdentity]:
        row = await self._fetchrow(
            """
            SELECT ci.* FROM dt_configuration_identities ci
            JOIN dt_identity_mappings im ON ci.identity_id = im.identity_id
            WHERE im.domain = $1 AND im.domain_id = $2
            """,
            domain,
            domain_id,
        )
        return ConfigurationIdentity.from_row(row) if row else None

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[ConfigurationIdentity]:
        rows = await self._fetch(
            "SELECT * FROM dt_configuration_identities ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        return [ConfigurationIdentity.from_row(r) for r in rows]