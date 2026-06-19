from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.configuration_management.configuration_change_control_service import (
    ConfigurationChangeControlService,
    ConfigurationChangeRequest,
    ChangeClass,
)

router = APIRouter(prefix="/api/v6/workflow-engine", tags=["Config Change Control v6"])

_change_service = ConfigurationChangeControlService()


@router.post("/config-change-requests")
async def submit_change_request(body: dict[str, Any]):
    request = ConfigurationChangeRequest(
        request_id=body.get("request_id", ""),
        block_id=body.get("block_id", ""),
        change_class=ChangeClass(body.get("change_class", "ClassII")),
        change_type=body.get("change_type", ""),
        description=body.get("description", ""),
        requested_by=body.get("requested_by", ""),
        affected_items=body.get("affected_items", []),
    )
    try:
        result = _change_service.submitChangeRequest(request=request)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/config-change-requests/{request_id}/impact-analysis")
async def perform_impact_analysis(request_id: str):
    try:
        result = _change_service.performImpactAnalysis(request_id=request_id)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/config-change-requests/{request_id}/approve")
async def approve_change_request(request_id: str, body: dict[str, Any]):
    approver = body.get("approver", "")
    change_class = ChangeClass(body.get("change_class", "ClassII"))
    try:
        result = _change_service.approveChangeRequest(
            request_id=request_id, approver=approver, change_class=change_class
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/config-change-requests/{request_id}/implement")
async def implement_change(request_id: str):
    try:
        result = _change_service.implementChange(request_id=request_id)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/config-change-requests/{request_id}/verify")
async def verify_change(request_id: str):
    try:
        result = _change_service.verifyChange(request_id=request_id)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))