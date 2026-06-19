from __future__ import annotations

import uuid
from typing import Any

from src.domain.entities.physics_simulation import PhysicsSimulation
from src.domain.enums import SimulationStatus, SolverType


class SimulationExecutionService:

    @staticmethod
    async def submit_simulation(model_id: str, solver_type: SolverType,
                                boundary_conditions: dict[str, Any] | None = None,
                                config: dict[str, Any] | None = None, pool=None) -> PhysicsSimulation:
        sim = PhysicsSimulation(
            simulation_id=str(uuid.uuid4()),
            model_id=model_id,
            solver_type=solver_type,
            boundary_conditions=boundary_conditions or {},
            config=config or {},
        )

        if pool:
            async with pool.acquire() as conn:
                model_row = await conn.fetchrow(
                    "SELECT status, parameter_mappings FROM physics_twin.physics_models WHERE model_id = $1", model_id
                )
                if model_row is None:
                    raise ValueError(f"Model {model_id} not found")

                await conn.execute(
                    "INSERT INTO physics_twin.physics_simulations (simulation_id, model_id, solver_type, config, boundary_conditions, status) "
                    "VALUES ($1, $2, $3, $4, $5, $6)",
                    sim.simulation_id, model_id, solver_type.value,
                    config or {}, boundary_conditions or {}, SimulationStatus.Queued.value,
                )

        return sim

    @staticmethod
    async def get_simulation_status(simulation_id: str, pool) -> dict[str, Any] | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM physics_twin.physics_simulations WHERE simulation_id = $1", simulation_id
            )
            if row is None:
                return None
            return dict(row)

    @staticmethod
    async def cancel_simulation(simulation_id: str, pool) -> dict[str, Any]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE physics_twin.physics_simulations SET status = 'Failed', completed_at = NOW() WHERE simulation_id = $1",
                simulation_id,
            )
        return {"simulation_id": simulation_id, "status": "Failed"}

    @staticmethod
    async def retry_simulation(simulation_id: str, config_overrides: dict[str, Any] | None = None, pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE physics_twin.physics_simulations SET status = 'Queued', completed_at = NULL WHERE simulation_id = $1",
                simulation_id,
            )
        return {"simulation_id": simulation_id, "status": "Queued"}

    @staticmethod
    async def get_results(simulation_id: str, pool) -> dict[str, Any] | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM physics_twin.physics_simulations WHERE simulation_id = $1", simulation_id
            )
            if row is None:
                return None
            result = dict(row)
            return result