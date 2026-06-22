from __future__ import annotations

from typing import Optional

from src.infrastructure.repositories.base_repository import AsyncpgRepository
from src.domain.models.corrective_action_request import CorrectiveActionRequest


class CARRepository(AsyncpgRepository):

    async def create(
        self,
        ndt_record_id: str,
        description: str,
        responsible_person: str,
    ) -> CorrectiveActionRequest:
        row = await self._fetchrow(
            """
            INSERT INTO dt_corrective_actions
                (ndt_record_id, description, status, responsible_person)
            VALUES ($1::uuid, $2, 'open', $3)
            RETURNING *
            """,
            ndt_record_id,
            description,
            responsible_person,
        )
        return CorrectiveActionRequest.from_row(row)

    async def find_by_id(self, car_id: str) -> Optional[CorrectiveActionRequest]:
        row = await self._fetchrow(
            "SELECT * FROM dt_corrective_actions WHERE car_id = $1::uuid",
            car_id,
        )
        return CorrectiveActionRequest.from_row(row) if row else None

    async def find_by_ndt_record(self, ndt_record_id: str) -> list[CorrectiveActionRequest]:
        rows = await self._fetch(
            "SELECT * FROM dt_corrective_actions WHERE ndt_record_id = $1::uuid ORDER BY created_at DESC",
            ndt_record_id,
        )
        return [CorrectiveActionRequest.from_row(r) for r in rows]

    async def update_status(
        self,
        car_id: str,
        status: str,
        closed_by: Optional[str] = None,
    ) -> Optional[CorrectiveActionRequest]:
        closed_at_clause = ", closed_at = NOW()" if status == "closed" else ""
        row = await self._fetchrow(
            f"""
            UPDATE dt_corrective_actions
            SET status = $2, updated_at = NOW(){closed_at_clause}
            WHERE car_id = $1::uuid
            RETURNING *
            """,
            car_id,
            status,
        )
        return CorrectiveActionRequest.from_row(row) if row else None