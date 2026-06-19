from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse, AsyncTaskResponse

from ..domain.entities.thermal_task import ThermalAnalysisType, ThermalTask
from ..domain.services.thermal_domain_service import ThermalDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cae/thermal", tags=["Thermal"])

_thermal_service = ThermalDomainService()
_thermal_tasks: dict[str, ThermalTask] = {}


class HeatSourceRequest(BaseModel):
    name: str
    source_type: str = "volumetric"
    region: str = ""
    power_watts: float = 0.0


class ThermalBCRequest(BaseModel):
    name: str
    bc_type: str = "convection"
    region: str = ""
    h_coeff: float = 25.0
    ambient_temp_c: float = 25.0


class CoolantRequest(BaseModel):
    coolant_type: str = "water"
    flow_rate_lpm: float = 5.0
    inlet_temp_c: float = 20.0


class ThermalSubmitRequest(BaseModel):
    model_id: str
    analysis_type: str = "steady_state"
    mesh_task_id: str | None = None
    heat_sources: list[HeatSourceRequest] | None = None
    thermal_boundary_conditions: list[ThermalBCRequest] | None = None
    coolant: CoolantRequest | None = None


@router.post("/submit", response_model=AsyncTaskResponse)
async def submit_thermal_analysis(body: ThermalSubmitRequest):
    from ..domain.entities.thermal_task import CoolantParams, HeatSource, ThermalBoundaryCondition

    task = _thermal_service.submit_analysis(
        model_id=body.model_id,
        analysis_type=ThermalAnalysisType(body.analysis_type),
        mesh_task_id=body.mesh_task_id,
    )

    if body.heat_sources:
        for hs in body.heat_sources:
            task.add_heat_source(HeatSource(
                name=hs.name, source_type=hs.source_type,
                region=hs.region, power_watts=hs.power_watts,
            ))

    if body.thermal_boundary_conditions:
        for tbc in body.thermal_boundary_conditions:
            task.add_thermal_bc(ThermalBoundaryCondition(
                name=tbc.name, bc_type=tbc.bc_type, region=tbc.region,
                h_coeff=tbc.h_coeff, ambient_temp_c=tbc.ambient_temp_c,
            ))

    if body.coolant:
        task.set_coolant(CoolantParams(
            coolant_type=body.coolant.coolant_type,
            flow_rate_lpm=body.coolant.flow_rate_lpm,
            inlet_temp_c=body.coolant.inlet_temp_c,
        ))

    _thermal_tasks[task.id] = task

    try:
        task = _thermal_service.run_analysis(task)
    except Exception as exc:
        task.fail(str(exc))

    return AsyncTaskResponse(
        message="Thermal analysis submitted",
        task_id=task.id,
        status=task.status.value,
    )


@router.get("/{task_id}/status", response_model=ApiResponse[dict])
async def get_thermal_status(task_id: str):
    task = _thermal_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Thermal task not found")
    data: dict[str, Any] = {
        "task_id": task.id,
        "status": task.status.value,
        "progress_percent": task.progress_percent,
        "current_step": task.current_step,
    }
    return ApiResponse(data=data)


@router.get("/{task_id}/result", response_model=ApiResponse[dict])
async def get_thermal_result(task_id: str):
    task = _thermal_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Thermal task not found")
    if task.status.value not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Task not yet completed")
    data: dict[str, Any] = {
        "task_id": task.id,
        "model_id": task.model_id,
        "status": task.status.value,
        "analysis_type": task.analysis_type.value,
    }
    if task.result_summary:
        data["result_summary"] = task.result_summary.to_dict()
    if task.error_message:
        data["error_message"] = task.error_message
    return ApiResponse(data=data)