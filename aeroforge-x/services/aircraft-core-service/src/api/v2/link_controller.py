from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from src.domain.enums import LinkType
from src.domain.services.link_service import LinkService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class CreateLinkRequest(BaseModel):
    source_id: str
    target_id: str
    link_type: LinkType
    propagation_rule: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ImpactAnalysisRequest(BaseModel):
    max_depth: int = 5


@router.post("/links")
async def create_link(req: CreateLinkRequest):
    pool = await get_pg_pool()
    try:
        link = await LinkService.create_link(
            source_id=req.source_id,
            target_id=req.target_id,
            link_type=req.link_type,
            propagation_rule=req.propagation_rule,
            metadata=req.metadata,
            pool=pool,
        )
        return link.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/links/{link_id}")
async def delete_link(link_id: str):
    pool = await get_pg_pool()
    deleted = await LinkService.delete_link(link_id, pool)
    if not deleted:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"status": "deleted"}


@router.get("/objects/{object_id}/relationships")
async def get_relationships(object_id: str, depth: int = 1, link_type: str | None = None):
    pool = await get_pg_pool()
    lt = LinkType(link_type) if link_type else None
    result = await LinkService.get_relationships(object_id, link_type=lt, depth=depth, pool=pool)
    return result


@router.post("/objects/{object_id}/impact-analysis")
async def analyze_change_impact(object_id: str, req: ImpactAnalysisRequest):
    pool = await get_pg_pool()
    result = await LinkService.analyze_change_impact(object_id, max_depth=req.max_depth, pool=pool)
    return result