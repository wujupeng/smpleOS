from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class QmsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_plan(self, plan_data: dict[str, Any]) -> None:
        await self._session.execute(
            __import__("sqlalchemy").text(
                """INSERT INTO inspection_plans (id, plan_code, inspection_type, item_code, items, status, work_order_id, created_at)
                VALUES (:id, :plan_code, :inspection_type, :item_code, :items::jsonb, :status, :work_order_id, :created_at)
                ON CONFLICT (plan_code) DO UPDATE SET status = EXCLUDED.status
                """
            ),
            {**plan_data, "items": __import__("json").dumps(plan_data.get("items", []))},
        )

    async def save_record(self, record_data: dict[str, Any]) -> None:
        await self._session.execute(
            __import__("sqlalchemy").text(
                """INSERT INTO inspection_records
                (id, record_code, inspection_type, plan_id, item_code, result, inspector, inspection_date, criteria, measurements, notes, created_at)
                VALUES (:id, :record_code, :inspection_type, :plan_id, :item_code, :result, :inspector, :inspection_date, :criteria::jsonb, :measurements::jsonb, :notes, :created_at)
                """
            ),
            {
                **record_data,
                "criteria": __import__("json").dumps(record_data.get("criteria", {})),
                "measurements": __import__("json").dumps(record_data.get("measurements", {})),
            },
        )

    async def find_record_by_id(self, record_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            __import__("sqlalchemy").text("SELECT * FROM inspection_records WHERE id = :id"),
            {"id": record_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def find_latest_iqc_for_item(self, item_code: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            __import__("sqlalchemy").text(
                "SELECT * FROM inspection_records WHERE item_code = :item_code AND inspection_type = 'iqc' ORDER BY created_at DESC LIMIT 1"
            ),
            {"item_code": item_code},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def save_capa(self, capa_data: dict[str, Any]) -> None:
        await self._session.execute(
            __import__("sqlalchemy").text(
                """INSERT INTO capas
                (id, capa_code, root_cause, corrective_action, preventive_action, verification_result, status, due_date, escalated, inspection_record_id, created_by, created_at, updated_at)
                VALUES (:id, :capa_code, :root_cause, :corrective_action, :preventive_action, :verification_result, :status, :due_date, :escalated, :inspection_record_id, :created_by, :created_at, :updated_at)
                ON CONFLICT (capa_code) DO UPDATE SET
                    root_cause = EXCLUDED.root_cause, corrective_action = EXCLUDED.corrective_action,
                    preventive_action = EXCLUDED.preventive_action, verification_result = EXCLUDED.verification_result,
                    status = EXCLUDED.status, escalated = EXCLUDED.escalated, updated_at = EXCLUDED.updated_at
                """
            ),
            capa_data,
        )

    async def find_capa_by_id(self, capa_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            __import__("sqlalchemy").text("SELECT * FROM capas WHERE id = :id"),
            {"id": capa_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None