from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from src.domain.services.workflow_definition_service import WorkflowDefinitionService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class CreateDefinitionRequest(BaseModel):
    name: str
    nodes: list[dict]
    edges: list[dict]
    parameter_mappings: list[dict] | None = None


@router.post("/definitions")
async def create_definition(req: CreateDefinitionRequest):
    pool = await get_pg_pool()
    definition = await WorkflowDefinitionService.create_definition(
        name=req.name, nodes=req.nodes, edges=req.edges,
        parameter_mappings=req.parameter_mappings, pool=pool,
    )
    return definition.model_dump()


@router.get("/definitions")
async def list_definitions(status: str | None = None):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch("SELECT * FROM workflow_engine.workflow_definitions WHERE status = $1", status)
        else:
            rows = await conn.fetch("SELECT * FROM workflow_engine.workflow_definitions")
    return {"definitions": [dict(r) for r in rows]}


@router.get("/definitions/{definition_id}")
async def get_definition(definition_id: str):
    pool = await get_pg_pool()
    result = await WorkflowDefinitionService.get_definition(definition_id, pool)
    if result is None:
        raise HTTPException(status_code=404, detail="Definition not found")
    return result


@router.put("/definitions/{definition_id}")
async def update_definition(definition_id: str, req: CreateDefinitionRequest):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE workflow_engine.workflow_definitions SET name=$1, nodes=$2, edges=$3, parameter_mappings=$4, updated_at=NOW() WHERE definition_id=$5",
            req.name, req.nodes, req.edges, req.parameter_mappings or [], definition_id,
        )
    return {"status": "updated"}


@router.post("/definitions/{definition_id}/publish")
async def publish_definition(definition_id: str):
    pool = await get_pg_pool()
    definition = await WorkflowDefinitionService.publish_definition(definition_id, pool)
    if definition is None:
        raise HTTPException(status_code=404, detail="Definition not found")
    return definition.model_dump()


@router.post("/definitions/{definition_id}/deprecate")
async def deprecate_definition(definition_id: str):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE workflow_engine.workflow_definitions SET status = 'Deprecated', updated_at = NOW() WHERE definition_id = $1",
            definition_id,
        )
    return {"definition_id": definition_id, "status": "Deprecated"}