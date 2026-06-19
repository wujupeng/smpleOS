from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse, AsyncTaskResponse

from ..domain.entities.bom_item import EBOM, MBOM
from ..domain.services.ebom_engine import EBOMEngine
from ..domain.services.mbom_transform_domain_service import MBOMTransformDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bom/mbom", tags=["mBOM"])

_transform_service = MBOMTransformDomainService()
_ebom_engine = EBOMEngine()
_mbom_store: dict[str, MBOM] = {}
_ebom_store: dict[str, EBOM] = {}


class TransformMBOMRequest(BaseModel):
    ebom_id: str
    created_by: str = ""


class ConfirmMappingRequest(BaseModel):
    item_code: str
    target_station: str


@router.post("/transform", response_model=AsyncTaskResponse)
async def transform_ebom_to_mbom(body: TransformMBOMRequest):
    ebom = _ebom_store.get(body.ebom_id)
    if ebom is None:
        ebom = _ebom_engine.generate_from_model("SPEC-TRANSFORM", {})
        ebom.publish()
        _ebom_store[ebom.id] = ebom

    if ebom.root_item is None:
        raise HTTPException(status_code=400, detail="eBOM has no root item")

    mbom = _transform_service.transform_from_ebom(ebom, body.created_by)
    _mbom_store[mbom.id] = mbom

    return AsyncTaskResponse(
        message="mBOM transformation completed",
        task_id=mbom.id,
        status=mbom.status,
    )


@router.get("/{mbom_id}", response_model=ApiResponse[dict])
async def get_mbom(mbom_id: str):
    mbom = _mbom_store.get(mbom_id)
    if mbom is None:
        raise HTTPException(status_code=404, detail="mBOM not found")
    return ApiResponse(data=mbom.to_dict())


@router.get("/{mbom_id}/tree", response_model=ApiResponse[dict])
async def get_mbom_tree(mbom_id: str):
    mbom = _mbom_store.get(mbom_id)
    if mbom is None:
        raise HTTPException(status_code=404, detail="mBOM not found")
    if mbom.root_item is None:
        return ApiResponse(data={"mbom_id": mbom_id, "tree": None})
    return ApiResponse(data={
        "mbom_id": mbom_id,
        "mbom_code": mbom.mbom_code,
        "tree": mbom.root_item.to_dict(),
    })


@router.get("/{mbom_id}/unmapped", response_model=ApiResponse[dict])
async def get_unmapped_items(mbom_id: str):
    mbom = _mbom_store.get(mbom_id)
    if mbom is None:
        raise HTTPException(status_code=404, detail="mBOM not found")
    return ApiResponse(data={
        "mbom_id": mbom_id,
        "unmapped_count": len(mbom.unmapped_items),
        "unmapped_items": mbom.unmapped_items,
    })


@router.post("/{mbom_id}/confirm-mapping", response_model=ApiResponse[dict])
async def confirm_mapping(mbom_id: str, body: ConfirmMappingRequest):
    mbom = _mbom_store.get(mbom_id)
    if mbom is None:
        raise HTTPException(status_code=404, detail="mBOM not found")

    if mbom.root_item is None:
        raise HTTPException(status_code=400, detail="mBOM has no root item")

    all_items = mbom.root_item.flatten()
    target_item = next((i for i in all_items if i.item_code == body.item_code), None)
    if target_item is None:
        raise HTTPException(status_code=404, detail="Item not found in mBOM")

    target_item.mapping_status = "mapped"
    target_item.station = body.target_station

    mbom.unmapped_items = [
        u for u in mbom.unmapped_items
        if u.get("ebom_item_code") != body.item_code
    ]

    logger.info("Mapping confirmed: %s -> station %s", body.item_code, body.target_station)
    return ApiResponse(data={
        "mbom_id": mbom_id,
        "item_code": body.item_code,
        "target_station": body.target_station,
        "remaining_unmapped": len(mbom.unmapped_items),
    })


@router.post("/{mbom_id}/publish", response_model=ApiResponse[dict])
async def publish_mbom(mbom_id: str):
    mbom = _mbom_store.get(mbom_id)
    if mbom is None:
        raise HTTPException(status_code=404, detail="mBOM not found")

    try:
        mbom.publish()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ApiResponse(data={
        "mbom_id": mbom.id,
        "mbom_code": mbom.mbom_code,
        "status": mbom.status,
    })


@router.get("/{mbom_id}/validation", response_model=ApiResponse[dict])
async def get_mbom_validation(mbom_id: str):
    mbom = _mbom_store.get(mbom_id)
    if mbom is None:
        raise HTTPException(status_code=404, detail="mBOM not found")
    return ApiResponse(data={
        "mbom_id": mbom_id,
        "validation_result": mbom.validation_result,
    })