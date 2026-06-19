from __future__ import annotations

import uuid
from typing import Any

from src.domain.entities.physics_model import PhysicsModel
from src.domain.enums import FidelityLevel, HierarchyLevel, ModelStatus, PhysicsType


class PhysicsModelService:

    @staticmethod
    async def create_model(name: str, model_type: PhysicsType, hierarchy_level: HierarchyLevel,
                           fidelity_level: FidelityLevel, aircraft_object_id: str,
                           parameter_mappings: list[dict] | None = None, pool=None) -> PhysicsModel:
        model = PhysicsModel(
            model_id=str(uuid.uuid4()),
            name=name,
            type=model_type,
            hierarchy_level=hierarchy_level,
            fidelity_level=fidelity_level,
            aircraft_object_id=aircraft_object_id,
            parameter_mappings=parameter_mappings or [],
        )

        validation = model.validate_compatibility()
        if not validation["valid"]:
            raise ValueError(f"Model compatibility check failed: {validation['errors']}")

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO physics_twin.physics_models (model_id, name, model_type, hierarchy_level, fidelity_level, aircraft_object_id, parameter_mappings, status) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                    model.model_id, name, model_type.value, hierarchy_level.value,
                    fidelity_level.value, aircraft_object_id, parameter_mappings or [],
                    ModelStatus.Draft.value,
                )

        return model

    @staticmethod
    async def get_model(model_id: str, pool) -> PhysicsModel | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM physics_twin.physics_models WHERE model_id = $1", model_id)
            if row is None:
                return None
            return PhysicsModel(**dict(row))

    @staticmethod
    async def update_model(model_id: str, pool=None, **kwargs) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT status FROM physics_twin.physics_models WHERE model_id = $1", model_id)
            if row is None:
                return {"error": "Model not found"}
            if row["status"] in ("Deployed",):
                active_sims = await conn.fetchval(
                    "SELECT COUNT(*) FROM physics_twin.physics_simulations WHERE model_id = $1 AND status = 'Running'",
                    model_id,
                )
                if active_sims > 0:
                    raise ValueError("Cannot modify model while simulations are running")

        updates = []
        values = []
        idx = 0
        for key, val in kwargs.items():
            idx += 1
            updates.append(f"{key} = ${idx}")
            values.append(val)
        idx += 1
        updates.append(f"updated_at = NOW()")

        async with pool.acquire() as conn:
            await conn.execute(
                f"UPDATE physics_twin.physics_models SET {', '.join(updates)} WHERE model_id = ${idx}",
                *values, model_id,
            )
        return {"model_id": model_id, "status": "updated"}

    @staticmethod
    async def switch_fidelity(model_id: str, level: FidelityLevel, pool) -> PhysicsModel | None:
        model = await PhysicsModelService.get_model(model_id, pool)
        if model is None:
            return None
        model.switch_fidelity(level)
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE physics_twin.physics_models SET fidelity_level = $1, updated_at = NOW() WHERE model_id = $2",
                level.value, model_id,
            )
        return model

    @staticmethod
    async def map_parameters(model_id: str, mappings: list[dict], pool) -> dict[str, Any]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE physics_twin.physics_models SET parameter_mappings = $1, updated_at = NOW() WHERE model_id = $2",
                mappings, model_id,
            )
        return {"model_id": model_id, "parameter_mappings": mappings}

    @staticmethod
    async def list_models(aircraft_object_id: str | None = None, pool=None) -> list[dict[str, Any]]:
        async with pool.acquire() as conn:
            if aircraft_object_id:
                rows = await conn.fetch(
                    "SELECT * FROM physics_twin.physics_models WHERE aircraft_object_id = $1", aircraft_object_id
                )
            else:
                rows = await conn.fetch("SELECT * FROM physics_twin.physics_models")
        return [dict(r) for r in rows]