from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse, AsyncTaskResponse

from ..domain.entities.flutter_task import AerodynamicModel, FlutterTask
from ..domain.services.flutter_domain_service import FlutterDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cae/flutter", tags=["Flutter"])

_flutter_service = FlutterDomainService()
_flutter_tasks: dict[str, FlutterTask] = {}


class SpeedRangeRequest(BaseModel):
    min_speed_ms: float = Field(default=0.0, ge=0)
    max_speed_ms: float = Field(default=300.0, ge=0)
    speed_steps: int = Field(default=20, ge=5, le=100)


class FlutterSubmitRequest(BaseModel):
    model_id: str
    speed_range: SpeedRangeRequest | None = None
    aerodynamic_model: str = "quasi_steady"
    mesh_task_id: str | None = None


@router.post("/submit", response_model=AsyncTaskResponse)
async def submit_flutter_analysis(body: FlutterSubmitRequest):
    from ..domain.entities.flutter_task import SpeedRange

    sr = None
    if body.speed_range:
        sr = SpeedRange(
            min_speed_ms=body.speed_range.min_speed_ms,
            max_speed_ms=body.speed_range.max_speed_ms,
            speed_steps=body.speed_range.speed_steps,
        )

    task = _flutter_service.submit_analysis(
        model_id=body.model_id,
        speed_range=sr,
        aerodynamic_model=AerodynamicModel(body.aerodynamic_model),
        mesh_task_id=body.mesh_task_id,
    )

    _flutter_tasks[task.id] = task

    try:
        _flutter_service.compute_aeroelastic_stability(task)
    except Exception as exc:
        task.fail(str(exc))

    return AsyncTaskResponse(
        message="Flutter analysis submitted",
        task_id=task.id,
        status=task.status.value,
    )


@router.get("/{task_id}/status", response_model=ApiResponse[dict])
async def get_flutter_status(task_id: str):
    task = _flutter_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Flutter task not found")
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
async def get_flutter_result(task_id: str):
    task = _flutter_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Flutter task not found")
    if task.status.value not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Task not yet completed")
    data: dict[str, Any] = {
        "task_id": task.id,
        "model_id": task.model_id,
        "status": task.status.value,
        "aerodynamic_model": task.aerodynamic_model.value,
        "speed_range": task.speed_range.to_dict(),
        "structural_modes": [m.to_dict() for m in task.structural_modes],
    }
    if task.result_summary:
        data["result_summary"] = task.result_summary.to_dict()
    if task.error_message:
        data["error_message"] = task.error_message
    return ApiResponse(data=data)