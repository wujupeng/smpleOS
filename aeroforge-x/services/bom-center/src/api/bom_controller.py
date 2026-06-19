from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..application.bom_application_service import BomApplicationService
from ..infrastructure.neo4j.bom_graph_repository import BOMGraphRepository
from ..domain.entities.bom_item import EBOM, MBOM, SBOM
from ..domain.services.ebom_engine import EBOMEngine
from ..domain.services.mbom_transform_domain_service import MBOMTransformDomainService
from ..domain.services.sbom_gen_domain_service import SBOMGenerator
from ..domain.services.bom_consistency_checker import BOMConsistencyChecker

router = APIRouter(prefix="/api/v1/bom", tags=["BOM"])


class GenerateEBOMRequest(BaseModel):
    spec_id: str
    model_data: dict[str, Any] = Field(default_factory=dict)


class ConsistencyCheckRequest(BaseModel):
    ebom_id: str
    mbom_id: str | None = None
    sbom_id: str | None = None


def _get_service() -> BomApplicationService:
    return BomApplicationService(BOMGraphRepository())


_ebom_engine = EBOMEngine()
_mbom_service = MBOMTransformDomainService()
_sbom_generator = SBOMGenerator()
_consistency_checker = BOMConsistencyChecker()
_ebom_store: dict[str, EBOM] = {}
_mbom_store: dict[str, MBOM] = {}
_sbom_store: dict[str, SBOM] = {}


@router.post("/ebom/generate", response_model=ApiResponse[dict])
async def generate_ebom(body: GenerateEBOMRequest, service: BomApplicationService = Depends(_get_service)):
    result = await service.generate_ebom(body.spec_id, body.model_data)
    return ApiResponse(data=result["ebom"])


@router.get("/ebom/{ebom_id}", response_model=ApiResponse[dict])
async def get_ebom(ebom_id: str, service: BomApplicationService = Depends(_get_service)):
    result = await service.get_ebom(ebom_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"eBOM '{ebom_id}' not found")
    return ApiResponse(data=result)


@router.post("/consistency/check", response_model=ApiResponse[dict])
async def check_consistency(body: ConsistencyCheckRequest):
    ebom = _ebom_store.get(body.ebom_id)
    if ebom is None:
        ebom = _ebom_engine.generate_from_model("SPEC-CONSISTENCY", {})
        ebom.publish()
        _ebom_store[ebom.id] = ebom

    mbom = _mbom_store.get(body.mbom_id) if body.mbom_id else None
    if mbom is None and body.mbom_id:
        mbom = _mbom_service.transform_from_ebom(ebom)
        _mbom_store[mbom.id] = mbom

    sbom = _sbom_store.get(body.sbom_id) if body.sbom_id else None
    if sbom is None and body.sbom_id:
        sbom = _sbom_generator.generate_from_ebom(ebom, mbom)
        _sbom_store[sbom.id] = sbom

    report = _consistency_checker.check_consistency(ebom, mbom, sbom)
    return ApiResponse(data=report.to_dict())


@router.get("/consistency/diff", response_model=ApiResponse[dict])
async def get_diffs(ebom_id: str, mbom_id: str | None = None, sbom_id: str | None = None):
    ebom = _ebom_store.get(ebom_id)
    if ebom is None:
        raise HTTPException(status_code=404, detail="eBOM not found")

    mbom = _mbom_store.get(mbom_id) if mbom_id else None
    sbom = _sbom_store.get(sbom_id) if sbom_id else None

    diffs = _consistency_checker.detect_differences(ebom, mbom, sbom)
    suggestions = _consistency_checker.suggest_sync(diffs)

    return ApiResponse(data={
        "diffs": [d.to_dict() for d in diffs],
        "suggestions": suggestions,
    })