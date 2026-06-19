from __future__ import annotations

import uuid
from typing import Any

from src.domain.entities.digital_twin_runtime import DigitalTwinRuntime
from src.domain.enums import FidelityLevel, HealthStatus


class TwinRuntimeService:

    @staticmethod
    async def create_runtime(aircraft_object_id: str, pool=None) -> DigitalTwinRuntime:
        runtime = DigitalTwinRuntime(
            runtime_id=str(uuid.uuid4()),
            aircraft_object_id=aircraft_object_id,
        )

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO physics_twin.twin_runtimes (runtime_id, aircraft_object_id, active_fidelity, active_models, current_state, health_indicators, rul_predictions, data_lagged) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                    runtime.runtime_id, aircraft_object_id, FidelityLevel.Low.value,
                    [], {}, {}, [], False,
                )

        return runtime

    @staticmethod
    async def update_sensor_data(runtime_id: str, sensor_data: dict[str, Any], pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM physics_twin.twin_runtimes WHERE runtime_id = $1", runtime_id
            )
            if row is None:
                return {"error": "Runtime not found"}

            runtime = DigitalTwinRuntime(**dict(row))
            prediction = runtime.update_with_sensor_data(sensor_data)

            await conn.execute(
                "UPDATE physics_twin.twin_runtimes SET current_state = $1, data_lagged = $2, last_sensor_timestamp = $3, updated_at = NOW() WHERE runtime_id = $4",
                runtime.current_state, runtime.data_lagged, runtime.last_sensor_timestamp, runtime_id,
            )

        return prediction

    @staticmethod
    async def switch_runtime_fidelity(runtime_id: str, level: FidelityLevel, pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM physics_twin.twin_runtimes WHERE runtime_id = $1", runtime_id
            )
            if row is None:
                return {"error": "Runtime not found"}

            runtime = DigitalTwinRuntime(**dict(row))
            runtime.switch_fidelity(level)

            await conn.execute(
                "UPDATE physics_twin.twin_runtimes SET active_fidelity = $1, updated_at = NOW() WHERE runtime_id = $2",
                level.value, runtime_id,
            )

        return {"runtime_id": runtime_id, "active_fidelity": level.value}

    @staticmethod
    async def get_health_indicator(runtime_id: str, pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT health_indicators FROM physics_twin.twin_runtimes WHERE runtime_id = $1", runtime_id
            )
            if row is None:
                return {"error": "Runtime not found"}
            return {"runtime_id": runtime_id, "health_indicators": row["health_indicators"]}

    @staticmethod
    async def get_prediction(runtime_id: str, pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT current_state FROM physics_twin.twin_runtimes WHERE runtime_id = $1", runtime_id
            )
            if row is None:
                return {"error": "Runtime not found"}
            return {"runtime_id": runtime_id, "current_state": row["current_state"]}