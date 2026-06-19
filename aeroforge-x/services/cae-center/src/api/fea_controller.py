from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse, AsyncTaskResponse

from ..domain.entities.fea_task import (
    BCType,
    FEAAnalysisType,
    FEASolverType,
    FEATask,
    LoadType,
    MaterialProperties,
)
from ..domain.services.fea_domain_service import FEADomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cae/fea", tags=["FEA"])

_fea_service = FEADomainService()
_fea_tasks: dict[str, FEATask] = {}


class LoadCaseRequest(BaseModel):
    name: str
    load_type: str = "concentrated_force"
    region: str = ""
    values: dict[str, float] | None = None


class BoundaryConditionRequest(BaseModel):
    name: str
    bc_type: str = "fixed"
    region: str = ""
    values: dict[str, float] | None = None


class MaterialRequest(BaseModel):
    name: str = "steel"
    elastic_modulus_pa: float = Field(default=200e9)
    poisson_ratio: float = Field(default=0.3)
    density_kg_m3: float = Field(default=7850.0)
    thermal_expansion_coeff: float = Field(default=12e-6)
    yield_strength_pa: float = Field(default=250e6)
    ultimate_strength_pa: float = Field(default=400e6)


class FEASubmitRequest(BaseModel):
    model_id: str
    analysis_type: str = "strength"
    solver_type: str = "FEniCS"
    mesh_task_id: str | None = None
    load_cases: list[LoadCaseRequest] | None = None
    boundary_conditions: list[BoundaryConditionRequest] | None = None
    material: MaterialRequest | None = None


@router.post("/submit", response_model=AsyncTaskResponse)
async def submit_fea_analysis(body: FEASubmitRequest):
    from ..domain.entities.fea_task import LoadCase, BoundaryCondition

    task = _fea_service.submit_analysis(
        model_id=body.model_id,
        analysis_type=FEAAnalysisType(body.analysis_type),
        solver_type=FEASolverType(body.solver_type),
        mesh_task_id=body.mesh_task_id,
    )

    if body.load_cases:
        for lc in body.load_cases:
            task.add_load_case(LoadCase(
                name=lc.name,
                load_type=LoadType(lc.load_type),
                region=lc.region,
                values=lc.values or {},
            ))

    if body.boundary_conditions:
        for bc in body.boundary_conditions:
            task.add_boundary_condition(BoundaryCondition(
                name=bc.name,
                bc_type=BCType(bc.bc_type),
                region=bc.region,
                values=bc.values or {},
            ))

    if body.material:
        task.set_material(MaterialProperties(
            name=body.material.name,
            elastic_modulus_pa=body.material.elastic_modulus_pa,
            poisson_ratio=body.material.poisson_ratio,
            density_kg_m3=body.material.density_kg_m3,
            thermal_expansion_coeff=body.material.thermal_expansion_coeff,
            yield_strength_pa=body.material.yield_strength_pa,
            ultimate_strength_pa=body.material.ultimate_strength_pa,
        ))

    _fea_tasks[task.id] = task

    try:
        task = _fea_service.prepare_problem(task, f"/tmp/fea_mesh_{task.id}")
        _fea_service.execute_solver(task, f"/tmp/fea_mesh_{task.id}")
        task = _fea_service.post_process(task)
    except Exception as exc:
        task.fail(str(exc))

    return AsyncTaskResponse(
        message="FEA analysis submitted",
        task_id=task.id,
        status=task.status.value,
    )


@router.get("/{task_id}/status", response_model=ApiResponse[dict])
async def get_fea_status(task_id: str):
    task = _fea_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="FEA task not found")
    data: dict[str, Any] = {
        "task_id": task.id,
        "status": task.status.value,
        "progress_percent": task.progress_percent,
        "current_step": task.current_step,
    }
    if task.error_message:
        data["error_message"] = task.error_message
    return ApiResponse(data=data)


@router.get("/{task_id}/result", response_model=ApiResponse[dict])
async def get_fea_result(task_id: str):
    task = _fea_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="FEA task not found")
    if task.status.value not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Task not yet completed")
    data: dict[str, Any] = {
        "task_id": task.id,
        "model_id": task.model_id,
        "status": task.status.value,
        "analysis_type": task.analysis_type.value,
        "solver_type": task.solver_type.value,
    }
    if task.result_summary:
        data["result_summary"] = task.result_summary.to_dict()
    if task.error_message:
        data["error_message"] = task.error_message
    return ApiResponse(data=data)


@router.get("/{task_id}/visualization", response_model=ApiResponse[dict])
async def get_fea_visualization(task_id: str):
    task = _fea_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="FEA task not found")
    if task.status.value != "completed":
        raise HTTPException(status_code=400, detail="Task not completed")

    visualization_data: dict[str, Any] = {
        "task_id": task.id,
        "model_id": task.model_id,
        "plots": {
            "von_mises_stress": {
                "type": "contour",
                "field": "von_mises_stress",
                "unit": "Pa",
                "available": True,
            },
            "deformation": {
                "type": "vector_field",
                "field": "displacement",
                "unit": "m",
                "deformation_scale": 100.0,
                "available": True,
            },
            "fatigue_damage": {
                "type": "contour",
                "field": "fatigue_life",
                "unit": "cycles",
                "available": task.analysis_type == FEAAnalysisType.FATIGUE.value,
            },
        },
    }
    return ApiResponse(data=visualization_data)