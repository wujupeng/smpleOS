from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

from ..domain.services.plm_services import (
    ProductStructureService,
    VersionManagementService,
    BaselineManagementService,
    ChangeManagementService,
)

router = APIRouter(prefix="/api/v1/plm", tags=["PLM Center"])

_structure_svc = ProductStructureService()
_version_svc = VersionManagementService()
_baseline_svc = BaselineManagementService()
_change_svc = ChangeManagementService()


class CreateStructureRequest(BaseModel):
    product_id: str
    product_name: str


class CreateDesignObjectRequest(BaseModel):
    object_number: str = Field(..., min_length=1)
    object_type: str
    object_name: str = Field(..., min_length=1)
    owner_id: str | None = None


class CreateVersionRequest(BaseModel):
    change_summary: str = ""
    author_id: str | None = None


class CreateBaselineRequest(BaseModel):
    baseline_name: str = Field(..., min_length=1)
    baseline_type: str = "development"
    created_by: str | None = None


class FreezeBaselineRequest(BaseModel):
    frozen_by: str


class CreateECRRequest(BaseModel):
    ecr_number: str = Field(..., min_length=1)
    change_type: str
    title: str = Field(..., min_length=1)
    description: str
    priority: str = "medium"
    safety_critical: bool = False
    requested_by: str | None = None


class ApproveECRRequest(BaseModel):
    approver_id: str


class AnalyzeImpactRequest(BaseModel):
    affected_objects: list[dict]


class CreateECORequest(BaseModel):
    eco_number: str = Field(..., min_length=1)
    implementation_plan: str = ""


class CreateECNRequest(BaseModel):
    ecn_number: str = Field(..., min_length=1)
    description: str = ""
    effective_date: str | None = None


@router.post("/product-structure")
async def create_structure(req: CreateStructureRequest):
    result = _structure_svc.create_structure(req.product_id, req.product_name)
    return result


@router.get("/product-structure/{structure_id}/tree")
async def get_product_tree(structure_id: str):
    tree = _structure_svc.get_product_tree(structure_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Structure not found")
    return tree


@router.post("/versions")
async def create_design_object(req: CreateDesignObjectRequest):
    obj = _version_svc.create_object(req.object_number, req.object_type, req.object_name, req.owner_id)
    return obj.to_dict()


@router.get("/versions/item/{object_id}")
async def get_item_versions(object_id: str):
    try:
        versions = _version_svc.get_item_versions(object_id)
        return {"versions": versions}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/baselines")
async def create_baseline(req: CreateBaselineRequest):
    bl = _baseline_svc.create_baseline(req.baseline_name, req.baseline_type, req.created_by)
    return bl.to_dict()


@router.post("/baselines/{baseline_id}/freeze")
async def freeze_baseline(baseline_id: str, req: FreezeBaselineRequest):
    try:
        bl = _baseline_svc.freeze_baseline(baseline_id, req.frozen_by)
        return bl.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/baselines/{baseline_id}/comparison/{other_baseline_id}")
async def compare_baselines(baseline_id: str, other_baseline_id: str):
    try:
        return _baseline_svc.compare_baselines(baseline_id, other_baseline_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/changes")
async def create_ecr(req: CreateECRRequest):
    ecr = _change_svc.create_ecr(
        ecr_number=req.ecr_number, change_type=req.change_type, title=req.title,
        description=req.description, priority=req.priority,
        safety_critical=req.safety_critical, requested_by=req.requested_by,
    )
    return ecr.to_dict()


@router.post("/changes/{ecr_id}/submit")
async def submit_ecr(ecr_id: str):
    try:
        ecr = _change_svc.get_ecr(ecr_id)
        if not ecr:
            raise HTTPException(status_code=404, detail="ECR not found")
        ecr.submit()
        return ecr.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/changes/{ecr_id}/approve")
async def approve_ecr(ecr_id: str, req: ApproveECRRequest):
    try:
        ecr = _change_svc.approve_ecr(ecr_id, req.approver_id)
        return ecr.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/changes/{ecr_id}/implement")
async def implement_change(ecr_id: str):
    try:
        ecr = _change_svc.get_ecr(ecr_id)
        if not ecr:
            raise HTTPException(status_code=404, detail="ECR not found")
        eco = _change_svc.create_eco(ecr_id, eco_number=f"ECO-{ecr.ecr_number}")
        ecn = _change_svc.create_ecn(eco.eco_id, ecn_number=f"ECN-{ecr.ecr_number}")
        return {"ecr": ecr.to_dict(), "eco": eco.to_dict(), "ecn": ecn.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/changes")
async def list_changes(status: str | None = None):
    ecrs = _change_svc.list_ecrs(status=status)
    return {"changes": [e.to_dict() for e in ecrs], "total": len(ecrs)}