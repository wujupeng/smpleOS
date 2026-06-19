from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..domain.entities.aircraft_spec import AircraftSpec


class SpecRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, spec: AircraftSpec) -> None:
        data = spec.to_dict()
        await self._session.execute(
            __import__("sqlalchemy").text(
                """INSERT INTO aircraft_specs
                (id, spec_code, aircraft_type, payload_kg, range_km, cruise_speed_kmh,
                 takeoff_distance_m, power_type, budget_cny, material_id,
                 certification_level_id, derived_constraints, status, created_by,
                 confirmed_at, frozen_at, created_at, updated_at)
                VALUES (:id, :spec_code, :aircraft_type, :payload_kg, :range_km,
                 :cruise_speed_kmh, :takeoff_distance_m, :power_type, :budget_cny,
                 :material_id, :certification_level_id, :derived_constraints::jsonb,
                 :status, :created_by, :confirmed_at, :frozen_at, :created_at, :updated_at)
                ON CONFLICT (id) DO UPDATE SET
                    aircraft_type = EXCLUDED.aircraft_type,
                    payload_kg = EXCLUDED.payload_kg,
                    range_km = EXCLUDED.range_km,
                    cruise_speed_kmh = EXCLUDED.cruise_speed_kmh,
                    takeoff_distance_m = EXCLUDED.takeoff_distance_m,
                    power_type = EXCLUDED.power_type,
                    budget_cny = EXCLUDED.budget_cny,
                    material_id = EXCLUDED.material_id,
                    certification_level_id = EXCLUDED.certification_level_id,
                    derived_constraints = EXCLUDED.derived_constraints,
                    status = EXCLUDED.status,
                    confirmed_at = EXCLUDED.confirmed_at,
                    frozen_at = EXCLUDED.frozen_at,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            {**data, "derived_constraints": __import__("json").dumps(data.get("derived_constraints", {}))},
        )

    async def find_by_id(self, spec_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            __import__("sqlalchemy").text(
                "SELECT * FROM aircraft_specs WHERE id = :id"
            ),
            {"id": spec_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def find_all(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        result = await self._session.execute(
            __import__("sqlalchemy").text(
                "SELECT * FROM aircraft_specs ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            {"limit": limit, "offset": offset},
        )
        return [dict(row) for row in result.mappings().all()]

    async def count(self) -> int:
        result = await self._session.execute(
            __import__("sqlalchemy").text("SELECT COUNT(*) FROM aircraft_specs")
        )
        return result.scalar() or 0