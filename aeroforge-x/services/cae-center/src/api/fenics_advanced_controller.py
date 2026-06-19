from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.fenics_advanced import MeanStressCorrection
from ..domain.services.fenics_advanced_service import FEniCSAdvancedService

router = APIRouter(prefix="/api/v1/cae/fea", tags=["FEniCS Advanced"])

_service = FEniCSAdvancedService()
_custom_fea_tasks: dict = {}
_fatigue_tasks: dict = {}
_buckling_tasks: dict = {}


class CustomFEARequest(BaseModel):
    model_id: str
    project_id: str = "default"
    tenant_id: str = "default"
    ufl_filename: str
    ufl_content: str
    boundary_conditions: list[dict[str, Any]] | None = None
    material_props: dict[str, float] | None = None


class FatigueAnalysisRequest(BaseModel):
    model_id: str
    project_id: str = "default"
    tenant_id: str = "default"
    load_spectrum: list[float]
    sn_curve: list[dict[str, float]] | None = None
    mean_stress_correction: str = "goodman"
    endurance_limit: float = Field(default=1e7, gt=0)


class BucklingAnalysisRequest(BaseModel):
    model_id: str
    project_id: str = "default"
    tenant_id: str = "default"
    num_modes: int = Field(default=5, ge=1, le=50)


@router.post("/custom", response_model=ApiResponse[dict])
async def submit_custom_fea(body: CustomFEARequest):
    correction = MeanStressCorrection(body.mean_stress_correction) if body.mean_stress_correction else MeanStressCorrection.GOODMAN
    task = _service.submit_custom_fea(
        model_id=body.model_id,
        project_id=body.project_id,
        tenant_id=body.tenant_id,
        ufl_filename=body.ufl_filename,
        ufl_content=body.ufl_content,
        boundary_conditions=body.boundary_conditions,
        material_props=body.material_props,
    )
    _custom_fea_tasks[task.id] = task
    return ApiResponse(data=task.to_dict())


@router.get("/custom/{task_id}", response_model=ApiResponse[dict])
async def get_custom_fea(task_id: str):
    task = _custom_fea_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Custom FEA task not found")
    return ApiResponse(data=task.to_dict())


@router.post("/fatigue", response_model=ApiResponse[dict])
async def submit_fatigue_analysis(body: FatigueAnalysisRequest):
    correction = MeanStressCorrection(body.mean_stress_correction)
    task = _service.run_fatigue_analysis(
        model_id=body.model_id,
        project_id=body.project_id,
        tenant_id=body.tenant_id,
        load_spectrum=body.load_spectrum,
        sn_curve=body.sn_curve,
        mean_stress_correction=correction,
        endurance_limit=body.endurance_limit,
    )
    _fatigue_tasks[task.id] = task
    return ApiResponse(data=task.to_dict())


@router.get("/fatigue/{task_id}", response_model=ApiResponse[dict])
async def get_fatigue_analysis(task_id: str):
    task = _fatigue_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Fatigue analysis not found")
    return ApiResponse(data=task.to_dict())


@router.post("/buckling", response_model=ApiResponse[dict])
async def submit_buckling_analysis(body: BucklingAnalysisRequest):
    task = _service.run_buckling_analysis(
        model_id=body.model_id,
        project_id=body.project_id,
        tenant_id=body.tenant_id,
        num_modes=body.num_modes,
    )
    _buckling_tasks[task.id] = task
    return ApiResponse(data=task.to_dict())


@router.get("/buckling/{task_id}", response_model=ApiResponse[dict])
async def get_buckling_analysis(task_id: str):
    task = _buckling_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Buckling analysis not found")
    return ApiResponse(data=task.to_dict())