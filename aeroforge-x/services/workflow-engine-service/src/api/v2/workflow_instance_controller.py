from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from src.domain.services.workflow_execution_service import WorkflowExecutionService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class StartInstanceRequest(BaseModel):
    definition_id: str
    definition_version: int = 1
    input_parameters: dict[str, Any] | None = None


@router.post("/instances")
async def start_instance(req: StartInstanceRequest):
    pool = await get_pg_pool()
    instance = await WorkflowExecutionService.start_instance(
        definition_id=req.definition_id,
        definition_version=req.definition_version,
        input_parameters=req.input_parameters,
        pool=pool,
    )
    return instance.model_dump()


@router.get("/instances/{instance_id}")
async def get_instance_status(instance_id: str):
    pool = await get_pg_pool()
    result = await WorkflowExecutionService.get_instance_status(instance_id, pool)
    if result is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    return result


@router.post("/instances/{instance_id}/suspend")
async def suspend_instance(instance_id: str):
    pool = await get_pg_pool()
    return await WorkflowExecutionService.suspend_instance(instance_id, pool)


@router.post("/instances/{instance_id}/resume")
async def resume_instance(instance_id: str):
    pool = await get_pg_pool()
    return await WorkflowExecutionService.resume_instance(instance_id, pool)


@router.post("/instances/{instance_id}/cancel")
async def cancel_instance(instance_id: str):
    pool = await get_pg_pool()
    return await WorkflowExecutionService.cancel_instance(instance_id, pool)


@router.post("/instances/{instance_id}/nodes/{node_id}/retry")
async def retry_node(instance_id: str, node_id: str):
    pool = await get_pg_pool()
    return await WorkflowExecutionService.retry_node(instance_id, node_id, pool)