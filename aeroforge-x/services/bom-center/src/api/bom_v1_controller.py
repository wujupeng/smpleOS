from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

from ..domain.services.bom_services import EBOMService, BOMTransformService, BOMSyncService

router = APIRouter(prefix="/api/v1/bom", tags=["BOM Center"])

_ebom_svc = EBOMService()
_transform_svc = BOMTransformService(_ebom_svc)
_sync_svc = BOMSyncService(_ebom_svc, _transform_svc)


class GenerateEBOMRequest(BaseModel):
    bom_number: str = Field(..., min_length=1)
    product_id: str
    lines: list[dict] = []
    created_by: str | None = None


class TransformBOMRequest(BaseModel):
    ebom_id: str
    bom_number: str = Field(..., min_length=1)
    created_by: str | None = None


class SyncBOMRequest(BaseModel):
    ebom_id: str
    target_bom_id: str
    target_type: str


@router.post("/ebom")
async def generate_ebom(req: GenerateEBOMRequest):
    try:
        ebom = _ebom_svc.generate_ebom(req.bom_number, req.product_id, req.lines, req.created_by)
        return ebom.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ebom/{bom_id}")
async def get_ebom(bom_id: str):
    ebom = _ebom_svc.get_ebom(bom_id)
    if not ebom:
        raise HTTPException(status_code=404, detail="eBOM not found")
    return ebom.to_dict()


@router.get("/ebom/{bom_id}/tree")
async def get_ebom_tree(bom_id: str):
    try:
        tree = _ebom_svc.get_ebom_tree(bom_id)
        return {"lines": tree, "total": len(tree)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ebom/{bom_id}/transform-to-mbom")
async def transform_to_mbom(bom_id: str, req: TransformBOMRequest):
    try:
        mbom = _transform_svc.transform_to_mbom(bom_id, req.bom_number, req.created_by)
        return mbom.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ebom/{bom_id}/transform-to-sbom")
async def transform_to_sbom(bom_id: str, req: TransformBOMRequest):
    try:
        sbom = _transform_svc.transform_to_sbom(bom_id, req.bom_number, req.created_by)
        return sbom.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mbom/{bom_id}")
async def get_mbom(bom_id: str):
    mbom = _transform_svc.get_mbom(bom_id)
    if not mbom:
        raise HTTPException(status_code=404, detail="mBOM not found")
    return mbom.to_dict()


@router.get("/sbom/{bom_id}")
async def get_sbom(bom_id: str):
    sbom = _transform_svc.get_sbom(bom_id)
    if not sbom:
        raise HTTPException(status_code=404, detail="sBOM not found")
    return sbom.to_dict()


@router.get("/ebom/{bom_id}/diff-mbom")
async def diff_ebom_mbom(bom_id: str, target_bom_id: str):
    try:
        diffs = _sync_svc.detect_differences(bom_id, "mbom", target_bom_id)
        return {"differences": diffs, "total": len(diffs)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/mbom/{bom_id}/sync")
async def sync_bom(bom_id: str, req: SyncBOMRequest):
    try:
        result = _sync_svc.sync_bom(req.ebom_id, req.target_type, bom_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))