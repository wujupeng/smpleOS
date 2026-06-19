from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse, AsyncTaskResponse

from ..domain.entities.multiphysics_task import (
    CouplingScheme,
    CouplingType,
    ConvergenceCriteria,
    MultiphysicsTask,
)
from ..domain.services.multiphysics_domain_service import MultiphysicsDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cae/multiphysics", tags=["Multiphysics"])

_multiphysics_service = MultiphysicsDomainService()
_multiphysics_tasks: dict[str, MultiphysicsTask] = {}


class ConvergenceCriteriaRequest(BaseModel):
    residual_tolerance: float = Field(default=1e-4)
    max_iterations: int = Field(default=10, ge=1, le=100)
    relaxation_factor: float = Field(default=0.7, ge=0.0, le=1.0)


class MultiphysicsSubmitRequest(BaseModel):
    model_id: str
    coupling_type: str = "aero_structural"
    coupling_scheme: str = "explicit_weak"
    convergence_criteria: ConvergenceCriteriaRequest | None = None


@router.post("/submit", response_model=AsyncTaskResponse)
async def submit_multiphysics_analysis(body: MultiphysicsSubmitRequest):
    criteria = None
    if body.convergence_criteria:
        criteria = ConvergenceCriteria(
            residual_tolerance=body.convergence_criteria.residual_tolerance,
            max_iterations=body.convergence_criteria.max_iterations,
            relaxation_factor=body.convergence_criteria.relaxation_factor,
        )

    task = _multiphysics_service.submit_coupled_analysis(
        model_id=body.model_id,
        coupling_type=CouplingType(body.coupling_type),
        coupling_scheme=CouplingScheme(body.coupling_scheme),
        convergence_criteria=criteria,
    )

    _multiphysics_tasks[task.id] = task

    try:
        task = _multiphysics_service.orchestrate_solvers(task)
    except Exception as exc:
        task.fail(str(exc))

    return AsyncTaskResponse(
        message="Multiphysics analysis submitted",
        task_id=task.id,
        status=task.status.value,
    )


@router.get("/{task_id}/status", response_model=ApiResponse[dict])
async def get_multiphysics_status(task_id: str):
    task = _multiphysics_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Multiphysics task not found")
    data: dict[str, Any] = {
        "task_id": task.id,
        "status": task.status.value,
        "progress_percent": task.progress_percent,
        "current_step": task.current_step,
        "coupling_type": task.coupling_type.value,
        "participant_solvers": task.participant_solvers,
    }
    if task.result_summary:
        data["current_iteration"] = task.result_summary.iterations_completed
        data["solver_statuses"] = [s.to_dict() for s in task.result_summary.solver_statuses]
    return ApiResponse(data=data)


@router.get("/{task_id}/result", response_model=ApiResponse[dict])
async def get_multiphysics_result(task_id: str):
    task = _multiphysics_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Multiphysics task not found")
    if task.status.value not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Task not yet completed")
    data: dict[str, Any] = {
        "task_id": task.id,
        "model_id": task.model_id,
        "status": task.status.value,
        "coupling_type": task.coupling_type.value,
        "coupling_scheme": task.coupling_scheme.value,
    }
    if task.result_summary:
        data["result_summary"] = task.result_summary.to_dict()
    if task.error_message:
        data["error_message"] = task.error_message
    return ApiResponse(data=data)