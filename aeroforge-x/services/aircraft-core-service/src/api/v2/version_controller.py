from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.domain.services.version_service import VersionService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class FrozenBaselineRequest(BaseModel):
    version_numbers: list[int]


class ReleasedBaselineRequest(BaseModel):
    version_numbers: list[int]
    lifecycle_stage: str


@router.get("/objects/{object_id}/versions")
async def get_version_history(object_id: str):
    pool = await get_pg_pool()
    versions = await VersionService.get_version_history(object_id, pool)
    return {"versions": [v.model_dump() for v in versions]}


@router.get("/objects/{object_id}/versions/{version_number}")
async def get_version(object_id: str, version_number: int):
    pool = await get_pg_pool()
    version = await VersionService.get_version(object_id, version_number, pool)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return version.model_dump()


@router.get("/objects/{object_id}/versions/diff")
async def diff_versions(object_id: str, v1: int, v2: int):
    pool = await get_pg_pool()
    result = await VersionService.diff_versions(object_id, v1, v2, pool)
    return result


@router.post("/objects/{object_id}/baselines/frozen")
async def create_frozen_baseline(object_id: str, req: FrozenBaselineRequest):
    pool = await get_pg_pool()
    result = await VersionService.create_frozen_baseline(object_id, req.version_numbers, pool)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/objects/{object_id}/baselines/released")
async def create_released_baseline(object_id: str, req: ReleasedBaselineRequest):
    pool = await get_pg_pool()
    result = await VersionService.create_released_baseline(object_id, req.version_numbers, req.lifecycle_stage, pool)
    return result