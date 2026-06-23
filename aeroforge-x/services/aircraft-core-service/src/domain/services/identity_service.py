from __future__ import annotations

import logging
from typing import Optional

import asyncpg

from src.infrastructure.repositories.configuration_identity_repository import ConfigurationIdentityRepository
from src.infrastructure.repositories.identity_mapping_repository import IdentityMappingRepository
from src.domain.models.configuration_identity import ConfigurationIdentity

logger = logging.getLogger(__name__)


class IdentityService:
    def __init__(self, pool: asyncpg.Pool):
        self._identity_repo = ConfigurationIdentityRepository(pool)
        self._mapping_repo = IdentityMappingRepository(pool)

    async def resolve_or_create_identity(
        self,
        domain: str,
        domain_id: str,
        label: str,
        node_type: str,
        related_domain: Optional[str] = None,
        related_domain_id: Optional[str] = None,
    ) -> ConfigurationIdentity:
        existing_mapping = await self._mapping_repo.find_by_domain(domain, domain_id)
        if existing_mapping:
            identity = await self._identity_repo.find_by_id(existing_mapping.identity_id)
            if identity:
                return identity

        target_identity_id = None
        if related_domain and related_domain_id:
            related_mapping = await self._mapping_repo.find_by_domain(related_domain, related_domain_id)
            if related_mapping:
                target_identity_id = related_mapping.identity_id

        if target_identity_id:
            identity = await self._identity_repo.find_by_id(target_identity_id)
            if identity is None:
                identity = await self._identity_repo.create(label=label, node_type=node_type)
                target_identity_id = identity.identity_id
        else:
            identity = await self._identity_repo.create(label=label, node_type=node_type)
            target_identity_id = identity.identity_id

        await self._mapping_repo.upsert(target_identity_id, domain, domain_id)

        if related_domain and related_domain_id:
            existing_rel = await self._mapping_repo.find_by_domain(related_domain, related_domain_id)
            if not existing_rel:
                await self._mapping_repo.upsert(target_identity_id, related_domain, related_domain_id)

        return identity

    async def get_identity(self, identity_id: str) -> Optional[dict]:
        identity = await self._identity_repo.find_by_id(identity_id)
        if identity is None:
            return None
        mappings = await self._mapping_repo.find_by_identity(identity_id)
        result = identity.to_dict()
        result["mappings"] = [m.to_dict() for m in mappings]
        return result

    async def get_identity_by_domain(self, domain: str, domain_id: str) -> Optional[dict]:
        mapping = await self._mapping_repo.find_by_domain(domain, domain_id)
        if mapping is None:
            return None
        return await self.get_identity(mapping.identity_id)

    async def list_identities(self, limit: int = 100, offset: int = 0) -> list[dict]:
        identities = await self._identity_repo.find_all(limit, offset)
        result = []
        for identity in identities:
            mappings = await self._mapping_repo.find_by_identity(identity.identity_id)
            d = identity.to_dict()
            d["mappings"] = [m.to_dict() for m in mappings]
            result.append(d)
        return result


_identity_service: IdentityService | None = None


async def get_identity_service() -> IdentityService:
    global _identity_service
    if _identity_service is not None:
        return _identity_service
    from src.infrastructure.database import get_pg_pool
    pool = await get_pg_pool()
    _identity_service = IdentityService(pool)
    return _identity_service