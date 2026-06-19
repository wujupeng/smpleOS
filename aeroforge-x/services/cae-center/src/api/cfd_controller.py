from __future__ import annotations

import logging
import tempfile
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse, AsyncTaskResponse

from ..domain.entities.cfd_task import (
    CFDAnalysisType,
    CFDSolverType,
    CFDTask,
    FlightConditions,
    TurbulenceModel,
)
from ..domain.services.cfd_domain_service import CFDDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cae/cfd", tags=["CFD"])

_cfd_service = CFDDomainService()
_cfd_tasks: dict[str, CFDTask] = {}


class FlightConditionsRequest(BaseModel):
    altitude_m: float = Field(default=0.0, ge=0)
    mach_number: float = Field(default=0.0, ge=0)
    reynolds_number: float = Field(default=0.0, ge=0)
    angle_of_attack_deg: float = Field(default=0.0)
    sideslip_angle_deg: float = Field(default=0.0)


class CFDSubmitRequest(BaseModel):
    model_id: str
    analysis_type: str = "steady"
    solver_type: str = "simpleFoam"
    turbulence_model: str = "kOmegaSST"
    flight_conditions: FlightConditionsRequest | None = None
    mesh_task_id: str | None = None
    n_proc: int = Field(default=1, ge=1)


@router.post("/submit", response_model=AsyncTaskResponse)
async def submit_cfd_analysis(body: CFDSubmitRequest):
    fc = None
    if body.flight_conditions:
        fc = FlightConditions(
            altitude_m=body.flight_conditions.altitude_m,
            mach_number=body.flight_conditions.mach_number,
            reynolds_number=body.flight_conditions.reynolds_number,
            angle_of_attack_deg=body.flight_conditions.angle_of_attack_deg,
            sideslip_angle_deg=body.flight_conditions.sideslip_angle_deg,
        )

    task = _cfd_service.submit_analysis(
        model_id=body.model_id,
        analysis_type=CFDAnalysisType(body.analysis_type),
        solver_type=CFDSolverType(body.solver_type),
        turbulence_model=TurbulenceModel(body.turbulence_model),
        flight_conditions=fc,
        mesh_task_id=body.mesh_task_id,
    )

    _cfd_tasks[task.id] = task

    case_dir = tempfile.mkdtemp(prefix=f"cfd_{task.id}_")
    try:
        task = _cfd_service.prepare_case(task, case_dir)
        task.start_running()
        task = _cfd_service.post_process(task)
    except Exception as exc:
        task.fail(str(exc))

    return AsyncTaskResponse(
        message="CFD analysis submitted",
        task_id=task.id,
        status=task.status.value,
    )


@router.get("/{task_id}/status", response_model=ApiResponse[dict])
async def get_cfd_status(task_id: str):
    task = _cfd_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="CFD task not found")
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
async def get_cfd_result(task_id: str):
    task = _cfd_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="CFD task not found")
    if task.status.value not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Task not yet completed")
    data: dict[str, Any] = {
        "task_id": task.id,
        "model_id": task.model_id,
        "status": task.status.value,
        "analysis_type": task.analysis_type.value,
        "solver_type": task.solver_type.value,
        "turbulence_model": task.turbulence_model.value,
        "flight_conditions": task.flight_conditions.to_dict(),
    }
    if task.result_summary:
        data["result_summary"] = task.result_summary.to_dict()
    if task.error_message:
        data["error_message"] = task.error_message
    return ApiResponse(data=data)


@router.get("/{task_id}/visualization", response_model=ApiResponse[dict])
async def get_cfd_visualization(task_id: str):
    task = _cfd_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="CFD task not found")
    if task.status.value != "completed":
        raise HTTPException(status_code=400, detail="Task not completed")

    visualization_data: dict[str, Any] = {
        "task_id": task.id,
        "model_id": task.model_id,
        "plots": {
            "pressure_contour": {
                "type": "contour",
                "field": "pressure",
                "available": bool(task.case_dir),
            },
            "velocity_vectors": {
                "type": "vector_field",
                "field": "velocity",
                "available": bool(task.case_dir),
            },
            "streamlines": {
                "type": "streamline",
                "field": "velocity",
                "available": bool(task.case_dir),
            },
            "residuals": {
                "type": "line_chart",
                "field": "residuals",
                "available": bool(task.case_dir),
            },
        },
        "paraview_state": f"/api/v1/cae/cfd/{task_id}/paraview.pvsm" if task.case_dir else None,
    }
    return ApiResponse(data=visualization_data)


@router.post("/{task_id}/retry", response_model=AsyncTaskResponse)
async def retry_cfd_analysis(task_id: str):
    old_task = _cfd_tasks.get(task_id)
    if old_task is None:
        raise HTTPException(status_code=404, detail="CFD task not found")
    if old_task.status.value not in ("failed",):
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

    new_task = _cfd_service.submit_analysis(
        model_id=old_task.model_id,
        analysis_type=old_task.analysis_type,
        solver_type=old_task.solver_type,
        turbulence_model=old_task.turbulence_model,
        flight_conditions=old_task.flight_conditions,
        mesh_task_id=old_task.mesh_task_id,
    )
    _cfd_tasks[new_task.id] = new_task

    case_dir = tempfile.mkdtemp(prefix=f"cfd_retry_{new_task.id}_")
    try:
        new_task = _cfd_service.prepare_case(new_task, case_dir)
        new_task.start_running()
        new_task = _cfd_service.post_process(new_task)
    except Exception as exc:
        new_task.fail(str(exc))

    return AsyncTaskResponse(
        message="CFD analysis retried",
        task_id=new_task.id,
        status=new_task.status.value,
    )