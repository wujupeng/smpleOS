from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.services.adaptive_scheduling_service import AdaptiveSchedulingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mes/adaptive-schedules", tags=["Adaptive Scheduling"])

_service = AdaptiveSchedulingService()


class CreateAdaptiveScheduleRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    base_schedule: dict[str, Any] | None = None


class DetectTriggerRequest(BaseModel):
    event_type: str = Field(..., description="station_failure|station_recovery|material_delay|urgent_insert|quality_anomaly|personnel_absence|deadline_change")
    event_data: dict[str, Any] = {}


class AdaptScheduleRequest(BaseModel):
    trigger_id: str = Field(..., min_length=1)
    constraints: dict[str, Any] | None = None


class MonitorExecutionRequest(BaseModel):
    actual_progress: dict[str, Any] = {}


@router.post("", response_model=ApiResponse[dict])
async def create_adaptive_schedule(body: CreateAdaptiveScheduleRequest):
    schedule = _service.create_adaptive_schedule(
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        name=body.name,
        base_schedule=body.base_schedule,
    )
    return ApiResponse(data=schedule.to_dict())


@router.get("/{schedule_id}", response_model=ApiResponse[dict])
async def get_adaptive_schedule(schedule_id: str):
    schedule = _service.get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Adaptive schedule not found")
    return ApiResponse(data=schedule.to_detail_dict())


@router.post("/{schedule_id}/detect-trigger", response_model=ApiResponse[dict])
async def detect_adaptation_trigger(schedule_id: str, body: DetectTriggerRequest):
    trigger = _service.detect_adaptation_trigger(
        schedule_id=schedule_id,
        event_type=body.event_type,
        event_data=body.event_data,
    )
    if trigger is None:
        raise HTTPException(status_code=400, detail="Failed to detect trigger")
    return ApiResponse(data=trigger.to_dict())


@router.post("/{schedule_id}/adapt", response_model=ApiResponse[dict])
async def adapt_schedule(schedule_id: str, body: AdaptScheduleRequest):
    try:
        record = _service.adapt_schedule(
            schedule_id=schedule_id,
            trigger_id=body.trigger_id,
            constraints=body.constraints,
        )
        return ApiResponse(data=record.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{schedule_id}/history", response_model=ApiResponse[dict])
async def get_adaptation_history(schedule_id: str):
    history = _service.get_adaptation_history(schedule_id)
    return ApiResponse(data={"schedule_id": schedule_id, "history": history, "total": len(history)})


@router.post("/{schedule_id}/monitor", response_model=ApiResponse[dict])
async def monitor_schedule_execution(schedule_id: str, body: MonitorExecutionRequest):
    result = _service.monitor_schedule_execution(schedule_id, body.actual_progress)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return ApiResponse(data=result)


@router.get("/{schedule_id}/learn", response_model=ApiResponse[dict])
async def learn_from_history(schedule_id: str):
    result = _service.learn_from_history(schedule_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return ApiResponse(data=result)


@router.post("/{schedule_id}/evaluate-impact", response_model=ApiResponse[dict])
async def evaluate_adaptation_impact(schedule_id: str, body: AdaptScheduleRequest):
    result = _service.evaluate_adaptation_impact(
        schedule_id=schedule_id,
        trigger_id=body.trigger_id,
        constraints=body.constraints,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return ApiResponse(data=result)