from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from src.domain.services.calibration_service import CalibrationService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class CalibrationRequest(BaseModel):
    runtime_id: str
    model_id: str


class ApplyCalibrationRequest(BaseModel):
    rollout_strategy: str = "immediate"


@router.post("/calibrations")
async def request_calibration(req: CalibrationRequest):
    pool = await get_pg_pool()
    try:
        calibration = await CalibrationService.request_calibration(
            runtime_id=req.runtime_id, model_id=req.model_id, pool=pool,
        )
        return calibration.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/calibrations/{calibration_id}")
async def get_calibration(calibration_id: str):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM physics_twin.twin_calibrations WHERE calibration_id = $1", calibration_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Calibration not found")
        return dict(row)


@router.post("/calibrations/{calibration_id}/validate")
async def validate_calibration(calibration_id: str, holdout_error: float, threshold: float = 0.05):
    pool = await get_pg_pool()
    result = await CalibrationService.validate_calibration(calibration_id, holdout_error, threshold, pool=pool)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/calibrations/{calibration_id}/apply")
async def apply_calibration(calibration_id: str, req: ApplyCalibrationRequest):
    pool = await get_pg_pool()
    result = await CalibrationService.apply_calibration(calibration_id, rollout_strategy=req.rollout_strategy, pool=pool)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result