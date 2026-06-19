from __future__ import annotations

import uuid
from typing import Any

from src.domain.entities.reduced_order_model import ReducedOrderModel
from src.domain.enums import ReductionMethod, ValidationStatus


class ModelReductionService:

    @staticmethod
    async def generate_rom(source_model_id: str, method: ReductionMethod, pool=None) -> ReducedOrderModel:
        if pool:
            async with pool.acquire() as conn:
                existing = await conn.fetchval(
                    "SELECT COUNT(*) FROM physics_twin.reduced_order_models WHERE source_model_id = $1 AND validation_status = 'Pending'",
                    source_model_id,
                )
                if existing > 0:
                    raise ValueError("A ROM generation is already in progress for this model")

        rom = ReducedOrderModel(
            rom_id=str(uuid.uuid4()),
            source_model_id=source_model_id,
            method=method,
        )

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO physics_twin.reduced_order_models (rom_id, source_model_id, reduction_method, validation_status, deployment_status) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    rom.rom_id, source_model_id, method.value,
                    ValidationStatus.Pending.value, "NotDeployed",
                )

        return rom

    @staticmethod
    async def validate_rom(rom_id: str, error_threshold: float = 0.05, pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM physics_twin.reduced_order_models WHERE rom_id = $1", rom_id
            )
            if row is None:
                return {"error": "ROM not found"}

            rom = ReducedOrderModel(**dict(row))
            rom.validate_rom(error_threshold)

            await conn.execute(
                "UPDATE physics_twin.reduced_order_models SET validation_error = $1, validation_status = $2 WHERE rom_id = $3",
                rom.validation_error, rom.validation_status.value, rom_id,
            )

        return {"rom_id": rom_id, "validation_status": rom.validation_status.value, "validation_error": rom.validation_error}

    @staticmethod
    async def deploy_rom(rom_id: str, runtime_id: str, pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM physics_twin.reduced_order_models WHERE rom_id = $1", rom_id
            )
            if row is None:
                return {"error": "ROM not found"}

            rom = ReducedOrderModel(**dict(row))
            try:
                rom.deploy(runtime_id)
            except ValueError as e:
                return {"error": str(e)}

            await conn.execute(
                "UPDATE physics_twin.reduced_order_models SET deployment_status = 'Deployed', deployed_ref = $1 WHERE rom_id = $2",
                runtime_id, rom_id,
            )

        return {"rom_id": rom_id, "deployment_status": "Deployed", "runtime_id": runtime_id}

    @staticmethod
    async def hot_swap_rom(rom_id: str, runtime_id: str, pool=None) -> dict[str, Any]:
        return await ModelReductionService.deploy_rom(rom_id, runtime_id, pool=pool)