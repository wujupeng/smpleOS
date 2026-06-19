from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from src.domain.enums import FidelityLevel
from src.domain.services.twin_runtime_service import TwinRuntimeService
from src.domain.services.health_assessment_service import HealthAssessmentService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class CreateRuntimeRequest(BaseModel):
    aircraft_object_id: str


class SensorDataInput(BaseModel):
    sensor_data: dict[str, Any]


class SwitchFidelityRequest(BaseModel):
    fidelity_level: FidelityLevel


@router.post("/runtimes")
async def create_runtime(req: CreateRuntimeRequest):
    pool = await get_pg_pool()
    runtime = await TwinRuntimeService.create_runtime(req.aircraft_object_id, pool=pool)
    return runtime.model_dump()


@router.get("/runtimes/{runtime_id}")
async def get_runtime_status(runtime_id: str):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM physics_twin.twin_runtimes WHERE runtime_id = $1", runtime_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Runtime not found")
        return dict(row)


@router.post("/runtimes/{runtime_id}/sensor-data")
async def push_sensor_data(runtime_id: str, req: SensorDataInput):
    pool = await get_pg_pool()
    result = await TwinRuntimeService.update_sensor_data(runtime_id, req.sensor_data, pool=pool)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/runtimes/{runtime_id}/switch-fidelity")
async def switch_fidelity(runtime_id: str, req: SwitchFidelityRequest):
    pool = await get_pg_pool()
    result = await TwinRuntimeService.switch_runtime_fidelity(runtime_id, req.fidelity_level, pool=pool)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/runtimes/{runtime_id}/health")
async def get_health(runtime_id: str):
    pool = await get_pg_pool()
    result = await TwinRuntimeService.get_health_indicator(runtime_id, pool=pool)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/runtimes/{runtime_id}/rul")
async def get_rul(runtime_id: str, component_id: str):
    pool = await get_pg_pool()
    prediction = HealthAssessmentService.predict_rul(
        component_id=component_id, degradation_rate=0.01, current_health=80.0
    )
    return prediction.model_dump()


@router.post("/runtimes/{runtime_id}/diagnose")
async def diagnose(runtime_id: str):
    pool = await get_pg_pool()
    result = HealthAssessmentService.diagnose_anomaly(
        predicted=100.0, measured=95.0, component_id="default"
    )
    return result