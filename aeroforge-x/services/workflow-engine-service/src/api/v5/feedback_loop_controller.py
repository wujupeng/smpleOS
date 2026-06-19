from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.manufacturing.twin_feedback_loop_service import (
    TwinFeedbackLoopService,
)

router = APIRouter(prefix="/api/v5/workflow-engine/feedback-loops", tags=["Feedback Loop v5"])

_service = TwinFeedbackLoopService()


@router.post("")
async def initiate_feedback_loop(body: dict[str, Any]):
    trigger_type = body.get("trigger_type", "TwinAnomaly")
    trigger_data = body.get("trigger_data", {})
    instance = _service.initiate_feedback_loop(
        trigger_type=trigger_type,
        trigger_data=trigger_data,
    )
    return instance.to_dict()


@router.post("/{instance_id}/advance")
async def advance_loop_stage(instance_id: str, body: dict[str, Any]):
    operator_id = body.get("operator_id", "system")
    stage_result = body.get("stage_result")
    try:
        instance = _service.advance_loop_stage(
            instance_id=instance_id,
            operator_id=operator_id,
            stage_result=stage_result,
        )
        return instance.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{instance_id}/pause")
async def pause_loop(instance_id: str, body: dict[str, Any]):
    operator_id = body.get("operator_id", "system")
    reason = body.get("reason", "")
    try:
        instance = _service.pause_loop(
            instance_id=instance_id,
            operator_id=operator_id,
            reason=reason,
        )
        return instance.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{instance_id}/resume")
async def resume_loop(instance_id: str, body: dict[str, Any]):
    operator_id = body.get("operator_id", "system")
    try:
        instance = _service.resume_loop(
            instance_id=instance_id,
            operator_id=operator_id,
        )
        return instance.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{instance_id}")
async def get_loop_status(instance_id: str):
    instance = _service.get_loop_status(instance_id=instance_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="Feedback loop instance not found")
    return instance.to_dict()