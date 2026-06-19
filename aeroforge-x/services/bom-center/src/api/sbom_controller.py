from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aeroforge_common.domain.responses import ApiResponse, AsyncTaskResponse

from ..domain.entities.bom_item import EBOM, MBOM, SBOM
from ..domain.services.ebom_engine import EBOMEngine
from ..domain.services.mbom_transform_domain_service import MBOMTransformDomainService
from ..domain.services.sbom_gen_domain_service import SBOMGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bom/sbom", tags=["sBOM"])

_sbom_generator = SBOMGenerator()
_ebom_engine = EBOMEngine()
_mbom_service = MBOMTransformDomainService()
_sbom_store: dict[str, SBOM] = {}
_ebom_store: dict[str, EBOM] = {}
_mbom_store: dict[str, MBOM] = {}


class GenerateSBOMRequest(BaseModel):
    ebom_id: str
    mbom_id: str | None = None
    environment: str = "standard"
    created_by: str = ""


@router.post("/generate", response_model=AsyncTaskResponse)
async def generate_sbom(body: GenerateSBOMRequest):
    ebom = _ebom_store.get(body.ebom_id)
    if ebom is None:
        ebom = _ebom_engine.generate_from_model("SPEC-SBOM", {})
        ebom.publish()
        _ebom_store[ebom.id] = ebom

    mbom = None
    if body.mbom_id:
        mbom = _mbom_store.get(body.mbom_id)
        if mbom is None:
            mbom = _mbom_service.transform_from_ebom(ebom)
            _mbom_store[mbom.id] = mbom

    sbom = _sbom_generator.generate_from_ebom(
        ebom=ebom,
        mbom=mbom,
        environment=body.environment,
        created_by=body.created_by,
    )
    _sbom_store[sbom.id] = sbom

    return AsyncTaskResponse(
        message="sBOM generation completed",
        task_id=sbom.id,
        status=sbom.status,
    )


@router.get("/{sbom_id}", response_model=ApiResponse[dict])
async def get_sbom(sbom_id: str):
    sbom = _sbom_store.get(sbom_id)
    if sbom is None:
        raise HTTPException(status_code=404, detail="sBOM not found")
    return ApiResponse(data=sbom.to_dict())


@router.get("/{sbom_id}/tree", response_model=ApiResponse[dict])
async def get_sbom_tree(sbom_id: str):
    sbom = _sbom_store.get(sbom_id)
    if sbom is None:
        raise HTTPException(status_code=404, detail="sBOM not found")
    if sbom.root_item is None:
        return ApiResponse(data={"sbom_id": sbom_id, "tree": None})
    return ApiResponse(data={
        "sbom_id": sbom_id,
        "sbom_code": sbom.sbom_code,
        "tree": sbom.root_item.to_dict(),
    })


@router.post("/{sbom_id}/publish", response_model=ApiResponse[dict])
async def publish_sbom(sbom_id: str):
    sbom = _sbom_store.get(sbom_id)
    if sbom is None:
        raise HTTPException(status_code=404, detail="sBOM not found")
    try:
        sbom.publish()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ApiResponse(data={
        "sbom_id": sbom.id,
        "sbom_code": sbom.sbom_code,
        "status": sbom.status,
    })