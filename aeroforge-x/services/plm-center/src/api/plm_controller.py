from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from aeroforge_db.pg import get_session
from aeroforge_common.domain.responses import ApiResponse

from ..application.plm_application_service import PlmApplicationService
from ..infrastructure.persistence import ProductTreeRepository, VersionRepository

router = APIRouter(prefix="/api/v1/plm", tags=["PLM"])


class CreateTreeRequest(BaseModel):
    name: str = Field(..., min_length=1)
    spec_id: str
    root_part_id: str
    root_name: str


class AddPartRequest(BaseModel):
    part_id: str
    name: str
    part_type: str = "part"
    quantity: int = 1


class CreateVersionRequest(BaseModel):
    object_id: str
    change_summary: str = ""
    snapshot: dict[str, Any] = {}


class CompareVersionsRequest(BaseModel):
    object_id: str
    major1: int
    minor1: int
    major2: int
    minor2: int


def _get_service(session: AsyncSession = Depends(get_session)) -> PlmApplicationService:
    return PlmApplicationService(ProductTreeRepository(session), VersionRepository(session))


@router.post("/products", response_model=ApiResponse[dict])
async def create_product_tree(body: CreateTreeRequest, service: PlmApplicationService = Depends(_get_service)):
    tree = await service.create_product_tree(body.name, body.spec_id, body.root_part_id, body.root_name, created_by="system")
    return ApiResponse(data=tree.to_dict())


@router.get("/products/{tree_id}/tree", response_model=ApiResponse[dict])
async def get_product_tree(tree_id: str, service: PlmApplicationService = Depends(_get_service)):
    result = await service.get_product_tree(tree_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Product tree '{tree_id}' not found")
    return ApiResponse(data=result)


@router.post("/products/{tree_id}/parts", response_model=ApiResponse[dict])
async def add_part(tree_id: str, body: AddPartRequest, service: PlmApplicationService = Depends(_get_service)):
    result = await service.add_part_to_tree(tree_id, "root", body.part_id, body.name, body.part_type, body.quantity)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Product tree '{tree_id}' not found or parent not found")
    return ApiResponse(data=result)


@router.get("/products/{tree_id}/parts/{part_id}/where-used", response_model=ApiResponse[dict])
async def where_used(tree_id: str, part_id: str, service: PlmApplicationService = Depends(_get_service)):
    result = await service.where_used(tree_id, part_id)
    return ApiResponse(data={"part_id": part_id, "used_in": result})


@router.get("/versions/{object_id}", response_model=ApiResponse[dict])
async def get_version_history(object_id: str, service: PlmApplicationService = Depends(_get_service)):
    versions = await service.get_version_history(object_id)
    return ApiResponse(data={"object_id": object_id, "versions": versions})


@router.post("/versions", response_model=ApiResponse[dict])
async def create_version(body: CreateVersionRequest, service: PlmApplicationService = Depends(_get_service)):
    version = await service.create_version(body.object_id, body.change_summary, "system", body.snapshot)
    return ApiResponse(data=version)


@router.post("/versions/diff", response_model=ApiResponse[dict])
async def compare_versions(body: CompareVersionsRequest, service: PlmApplicationService = Depends(_get_service)):
    result = await service.compare_versions(body.object_id, body.major1, body.minor1, body.major2, body.minor2)
    if result is None:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    return ApiResponse(data=result)