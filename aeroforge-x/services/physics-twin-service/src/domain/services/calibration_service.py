from __future__ import annotations

import uuid
from typing import Any

from src.domain.entities.twin_calibration import TwinCalibration
from src.domain.enums import CalibrationStatus


class CalibrationService:

    @staticmethod
    async def request_calibration(runtime_id: str, model_id: str, pool=None) -> TwinCalibration:
        if pool:
            async with pool.acquire() as conn:
                existing = await conn.fetchval(
                    "SELECT COUNT(*) FROM physics_twin.twin_calibrations WHERE runtime_id = $1 AND model_id = $2 AND status IN ('Pending', 'InProgress')",
                    runtime_id, model_id,
                )
                if existing > 0:
                    raise ValueError("A calibration is already in progress for this model and runtime")

        calibration = TwinCalibration(
            calibration_id=str(uuid.uuid4()),
            runtime_id=runtime_id,
            model_id=model_id,
        )

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO physics_twin.twin_calibrations (calibration_id, runtime_id, model_id, status) VALUES ($1, $2, $3, $4)",
                    calibration.calibration_id, runtime_id, model_id, CalibrationStatus.Pending.value,
                )

        return calibration

    @staticmethod
    async def execute_calibration(calibration_id: str, parameter_adjustments: dict[str, Any], pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM physics_twin.twin_calibrations WHERE calibration_id = $1", calibration_id
            )
            if row is None:
                return {"error": "Calibration not found"}

            calibration = TwinCalibration(**dict(row))
            calibration.execute()

            await conn.execute(
                "UPDATE physics_twin.twin_calibrations SET status = 'InProgress', parameter_adjustments = $1 WHERE calibration_id = $2",
                parameter_adjustments, calibration_id,
            )

        return {"calibration_id": calibration_id, "status": "InProgress"}

    @staticmethod
    async def validate_calibration(calibration_id: str, holdout_error: float, threshold: float = 0.05, pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM physics_twin.twin_calibrations WHERE calibration_id = $1", calibration_id
            )
            if row is None:
                return {"error": "Calibration not found"}

            calibration = TwinCalibration(**dict(row))
            passed = calibration.validate_calibration(holdout_error, threshold)

            if passed:
                calibration.complete()
                new_status = CalibrationStatus.Completed.value
            else:
                calibration.fail()
                new_status = CalibrationStatus.Failed.value

            await conn.execute(
                "UPDATE physics_twin.twin_calibrations SET status = $1, validation_results = $2, completed_at = NOW() WHERE calibration_id = $3",
                new_status, calibration.validation_results, calibration_id,
            )

        return {"calibration_id": calibration_id, "passed": passed, "holdout_error": holdout_error}

    @staticmethod
    async def apply_calibration(calibration_id: str, rollout_strategy: str = "immediate", pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM physics_twin.twin_calibrations WHERE calibration_id = $1", calibration_id
            )
            if row is None:
                return {"error": "Calibration not found"}

            if row["status"] != CalibrationStatus.Completed.value:
                return {"error": "Calibration must be completed and validated before applying"}

            if rollout_strategy == "gradual":
                return {"calibration_id": calibration_id, "status": "gradual_rollout_started", "initial_batch": 2}

            return {"calibration_id": calibration_id, "status": "applied", "rollout_strategy": rollout_strategy}