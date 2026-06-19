from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

from ..domain.services.config_services import (
    ConfigItemService,
    ConfigBaselineService,
    ConfigChangeService,
    ConfigCompatibilityService,
)

router = APIRouter(prefix="/api/v1/config", tags=["Configuration Management"])

_item_service = ConfigItemService()
_baseline_service = ConfigBaselineService()
_change_service = ConfigChangeService(_item_service)
_compatibility_service = ConfigCompatibilityService()


class CreateItemRequest(BaseModel):
    item_number: str = Field(..., min_length=1)
    item_name: str = Field(..., min_length=1)
    item_type: str
    description: str = ""
    owner_id: str | None = None
    properties: dict[str, Any] = {}


class UpdateItemRequest(BaseModel):
    item_name: str | None = None
    description: str | None = None
    properties: dict[str, Any] | None = None


class LifecycleTransitionRequest(BaseModel):
    lifecycle: str


class CreateBaselineRequest(BaseModel):
    baseline_name: str = Field(..., min_length=1)
    baseline_type: str = "product"
    description: str = ""
    aircraft_config: str | None = None
    created_by: str | None = None


class FreezeBaselineRequest(BaseModel):
    frozen_by: str


class CreateChangeRequest(BaseModel):
    change_type: str
    title: str = Field(..., min_length=1)
    description: str
    affected_items: list[dict] = []
    priority: str = "medium"
    requested_by: str | None = None


class ApproveChangeRequest(BaseModel):
    approver_id: str


class PropagateChangeRequest(BaseModel):
    impact_data: dict | None = None


class ValidateCompatibilityRequest(BaseModel):
    item_ids: list[str]


@router.post("/items")
async def create_item(req: CreateItemRequest):
    try:
        item = _item_service.create_item(
            item_number=req.item_number,
            item_name=req.item_name,
            item_type=req.item_type,
            description=req.description,
            owner_id=req.owner_id,
            properties=req.properties,
        )
        return item.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/items/{item_id}")
async def get_item(item_id: str):
    item = _item_service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.to_dict()


@router.put("/items/{item_id}")
async def update_item(item_id: str, req: UpdateItemRequest):
    try:
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        item = _item_service.update_item(item_id, **updates)
        return item.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/items/{item_id}/lifecycle")
async def transition_lifecycle(item_id: str, req: LifecycleTransitionRequest):
    try:
        item = _item_service.transition_lifecycle(item_id, req.lifecycle)
        return item.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/items")
async def search_items(item_type: str | None = None, status: str | None = None, skip: int = 0, limit: int = 50):
    items = _item_service.search_items(item_type=item_type, status=status, skip=skip, limit=limit)
    return {"items": [i.to_dict() for i in items], "total": len(items)}


@router.post("/baselines")
async def create_baseline(req: CreateBaselineRequest):
    baseline = _baseline_service.create_baseline(
        baseline_name=req.baseline_name,
        baseline_type=req.baseline_type,
        description=req.description,
        aircraft_config=req.aircraft_config,
        created_by=req.created_by,
    )
    return baseline.to_dict()


@router.get("/baselines/{baseline_id}")
async def get_baseline(baseline_id: str):
    baseline = _baseline_service.get_baseline(baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return baseline.to_dict()


@router.post("/baselines/{baseline_id}/freeze")
async def freeze_baseline(baseline_id: str, req: FreezeBaselineRequest):
    try:
        baseline = _baseline_service.freeze_baseline(baseline_id, req.frozen_by)
        return baseline.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/baselines/{baseline_id}/items")
async def get_baseline_items(baseline_id: str):
    try:
        items = _baseline_service.get_baseline_items(baseline_id)
        return {"items": items}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/baselines/{baseline_id}/comparison/{other_baseline_id}")
async def compare_baselines(baseline_id: str, other_baseline_id: str):
    try:
        return _baseline_service.compare_baselines(baseline_id, other_baseline_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/changes")
async def create_change(req: CreateChangeRequest):
    change = _change_service.create_change(
        change_type=req.change_type,
        title=req.title,
        description=req.description,
        affected_items=req.affected_items,
        priority=req.priority,
        requested_by=req.requested_by,
    )
    return change.to_dict()


@router.post("/changes/{change_id}/propagate")
async def propagate_change(change_id: str, req: PropagateChangeRequest):
    try:
        change = _change_service.propagate_change(change_id, req.impact_data)
        return change.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/changes/{change_id}/approve")
async def approve_change(change_id: str, req: ApproveChangeRequest):
    try:
        change = _change_service.approve_change(change_id, req.approver_id)
        return change.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/changes/{change_id}/implement")
async def implement_change(change_id: str):
    try:
        change = _change_service.implement_change(change_id)
        return change.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/changes/{change_id}/impact")
async def analyze_impact(change_id: str):
    try:
        return _change_service.analyze_impact(change_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/changes")
async def list_changes(status: str | None = None, skip: int = 0, limit: int = 50):
    return {"changes": [], "total": 0}


@router.post("/compatibility/validate")
async def validate_compatibility(req: ValidateCompatibilityRequest):
    items = []
    for item_id in req.item_ids:
        item = _item_service.get_item(item_id)
        if item:
            items.append(item)
    return _compatibility_service.validate_compatibility(items)
