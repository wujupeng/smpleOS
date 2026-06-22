from __future__ import annotations

from datetime import date
from typing import Optional

from src.infrastructure.repositories.base_repository import AsyncpgRepository
from src.domain.models.material_lot import MaterialLot


class MaterialLotRepository(AsyncpgRepository):

    async def create(
        self,
        material_code: str,
        material_name: str,
        supplier_id: str,
        manufacture_date: str,
        received_date: str,
        certificate_no: str,
        block_id: Optional[str] = None,
    ) -> MaterialLot:
        count = await self._fetchval(
            "SELECT COUNT(*) FROM dt_material_lots WHERE material_code = $1",
            material_code,
        )
        seq = (count or 0) + 1
        lot_id = f"{material_code}-{seq:03d}"

        mfg_date = date.fromisoformat(manufacture_date) if isinstance(manufacture_date, str) else manufacture_date
        rcv_date = date.fromisoformat(received_date) if isinstance(received_date, str) else received_date

        row = await self._fetchrow(
            """
            INSERT INTO dt_material_lots
                (lot_id, material_code, material_name, supplier_id,
                 manufacture_date, received_date, certificate_no, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            lot_id,
            material_code,
            material_name,
            supplier_id,
            mfg_date,
            rcv_date,
            certificate_no,
            "received",
        )

        if block_id:
            await self._execute(
                """
                INSERT INTO dt_block_materials (block_id, lot_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                block_id,
                lot_id,
            )

        return MaterialLot.from_row(row)

    async def find_by_id(self, lot_id: str) -> Optional[MaterialLot]:
        row = await self._fetchrow(
            "SELECT * FROM dt_material_lots WHERE lot_id = $1",
            lot_id,
        )
        return MaterialLot.from_row(row) if row else None

    async def find_by_block(self, block_id: str) -> list[MaterialLot]:
        rows = await self._fetch(
            """
            SELECT ml.* FROM dt_material_lots ml
            JOIN dt_block_materials bm ON ml.lot_id = bm.lot_id
            WHERE bm.block_id = $1
            ORDER BY ml.created_at DESC
            """,
            block_id,
        )
        return [MaterialLot.from_row(r) for r in rows]

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[MaterialLot]:
        rows = await self._fetch(
            "SELECT * FROM dt_material_lots ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        return [MaterialLot.from_row(r) for r in rows]