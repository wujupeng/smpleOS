from __future__ import annotations

import logging
import uuid
from typing import Optional

import asyncpg

from src.infrastructure.event_contract.schema_registry import schema_registry
from src.infrastructure.event_bus import event_bus

logger = logging.getLogger(__name__)


class EventContractService:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._registry = schema_registry

    async def validate_and_publish(self, event_type: str, payload: dict, subject: str) -> bool:
        is_valid, error_msg = self._registry.validate_event(event_type, payload)
        if not is_valid:
            logger.error(f"Schema validation FAILED for {event_type}: {error_msg}")
        else:
            logger.debug(f"Schema validation PASSED for {event_type}")

        try:
            await event_bus.publish_jetstream(subject, payload)
        except Exception as e:
            logger.warning(f"Event publish failed for {subject}: {e}")

        return is_valid

    async def check_idempotency(self, consumer_name: str, event_id: str, event_type: str = "") -> bool:
        try:
            result = await self._pool.execute(
                """
                INSERT INTO consumer_idempotency_records (consumer_name, event_id, event_type)
                VALUES ($1, $2, $3)
                ON CONFLICT (consumer_name, event_id) DO NOTHING
                """,
                consumer_name,
                event_id,
                event_type,
            )
            return "INSERT" in result
        except Exception as e:
            logger.error(f"Idempotency check failed: {e}")
            return True

    async def register_contract(self, event_type: str, schema: dict, version: str) -> dict:
        contract_id = str(uuid.uuid4())
        import json
        await self._pool.execute(
            """
            INSERT INTO event_contract_versions (contract_id, event_type, schema_version, schema_content)
            VALUES ($1::uuid, $2, $3, $4::jsonb)
            """,
            contract_id,
            event_type,
            version,
            json.dumps(schema),
        )
        self._registry.register_schema(event_type, schema, version)
        return {"contract_id": contract_id, "event_type": event_type, "version": version}

    async def list_contracts(self) -> list[dict]:
        rows = await self._pool.fetch(
            "SELECT contract_id, event_type, schema_version, is_active, created_at FROM event_contract_versions WHERE is_active = TRUE ORDER BY event_type"
        )
        return [dict(r) for r in rows]

    async def get_contract(self, event_type: str) -> Optional[dict]:
        row = await self._pool.fetchrow(
            "SELECT * FROM event_contract_versions WHERE event_type = $1 AND is_active = TRUE ORDER BY created_at DESC LIMIT 1",
            event_type,
        )
        return dict(row) if row else None


_event_contract_service: EventContractService | None = None


async def get_event_contract_service() -> EventContractService:
    global _event_contract_service
    if _event_contract_service is not None:
        return _event_contract_service
    from src.infrastructure.database import get_pg_pool
    pool = await get_pg_pool()
    _event_contract_service = EventContractService(pool)
    return _event_contract_service