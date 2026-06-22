from __future__ import annotations

from datetime import date
from typing import Optional

from src.infrastructure.repositories.base_repository import AsyncpgRepository
from src.domain.models.ndt_record import NDTRecord


class NDTRecordRepository(AsyncpgRepository):

    async def create(
        self,
        material_lot_id: str,
        test_type: str,
        result: str,
        inspector: str,
        test_date: str,
        notes: Optional[str] = None,
    ) -> NDTRecord:
        td = date.fromisoformat(test_date) if isinstance(test_date, str) else test_date
        row = await self._fetchrow(
            """
            INSERT INTO dt_ndt_records
                (material_lot_id, test_type, result, inspector, test_date, notes)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            material_lot_id,
            test_type,
            result,
            inspector,
            td,
            notes,
        )
        return NDTRecord.from_row(row)

    async def find_by_id(self, ndt_record_id: str) -> Optional[NDTRecord]:
        row = await self._fetchrow(
            "SELECT * FROM dt_ndt_records WHERE ndt_record_id = $1::uuid",
            ndt_record_id,
        )
        return NDTRecord.from_row(row) if row else None

    async def find_by_material_lot(self, material_lot_id: str) -> list[NDTRecord]:
        rows = await self._fetch(
            "SELECT * FROM dt_ndt_records WHERE material_lot_id = $1 ORDER BY created_at DESC",
            material_lot_id,
        )
        return [NDTRecord.from_row(r) for r in rows]