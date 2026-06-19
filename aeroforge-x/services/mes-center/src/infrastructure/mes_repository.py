from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class WorkOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, order_data: dict[str, Any]) -> None:
        await self._session.execute(
            __import__("sqlalchemy").text(
                """INSERT INTO work_orders
                (id, order_code, product_model, quantity, priority, status, route_id, station_id,
                 planned_start_date, planned_end_date, actual_start_date, actual_end_date,
                 created_by, created_at, updated_at)
                VALUES (:id, :order_code, :product_model, :quantity, :priority, :status, :route_id, :station_id,
                 :planned_start_date, :planned_end_date, :actual_start_date, :actual_end_date,
                 :created_by, :created_at, :updated_at)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status, station_id = EXCLUDED.station_id,
                    actual_start_date = EXCLUDED.actual_start_date, actual_end_date = EXCLUDED.actual_end_date,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            order_data,
        )

    async def find_by_id(self, order_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            __import__("sqlalchemy").text("SELECT * FROM work_orders WHERE id = :id"),
            {"id": order_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def find_all(self, offset: int = 0, limit: int = 20, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            result = await self._session.execute(
                __import__("sqlalchemy").text(
                    "SELECT * FROM work_orders WHERE status = :status ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                ),
                {"status": status, "limit": limit, "offset": offset},
            )
        else:
            result = await self._session.execute(
                __import__("sqlalchemy").text(
                    "SELECT * FROM work_orders ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                ),
                {"limit": limit, "offset": offset},
            )
        return [dict(row) for row in result.mappings().all()]

    async def count(self, status: str | None = None) -> int:
        if status:
            result = await self._session.execute(
                __import__("sqlalchemy").text("SELECT COUNT(*) FROM work_orders WHERE status = :status"),
                {"status": status},
            )
        else:
            result = await self._session.execute(
                __import__("sqlalchemy").text("SELECT COUNT(*) FROM work_orders")
            )
        return result.scalar() or 0


class StationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_all(self) -> list[dict[str, Any]]:
        result = await self._session.execute(
            __import__("sqlalchemy").text("SELECT * FROM stations ORDER BY name")
        )
        return [dict(row) for row in result.mappings().all()]

    async def find_by_id(self, station_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            __import__("sqlalchemy").text("SELECT * FROM stations WHERE id = :id"),
            {"id": station_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None


class SerialNumberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, sn_data: dict[str, Any]) -> None:
        await self._session.execute(
            __import__("sqlalchemy").text(
                """INSERT INTO serial_numbers
                (id, serial_number, item_code, batch_number, supplier, work_order_id,
                 manufacturing_date, installation_date, installer, flight_hours, status, created_at)
                VALUES (:id, :serial_number, :item_code, :batch_number, :supplier, :work_order_id,
                 :manufacturing_date, :installation_date, :installer, :flight_hours, :status, :created_at)
                ON CONFLICT (serial_number) DO UPDATE SET
                    status = EXCLUDED.status, work_order_id = EXCLUDED.work_order_id,
                    installation_date = EXCLUDED.installation_date, installer = EXCLUDED.installer,
                    flight_hours = EXCLUDED.flight_hours
                """
            ),
            {**sn_data, "id": sn_data.get("id", sn_data["serial_number"])},
        )

    async def find_by_sn(self, serial_number: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            __import__("sqlalchemy").text("SELECT * FROM serial_numbers WHERE serial_number = :sn"),
            {"sn": serial_number},
        )
        row = result.mappings().first()
        return dict(row) if row else None