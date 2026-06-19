from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from src.domain.enums import TriggerType
from src.domain.services.event_trigger_service import EventTriggerService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class CreateTriggerRequest(BaseModel):
    definition_id: str
    trigger_type: TriggerType
    event_pattern: str = ""
    cron_expression: str = ""
    condition: str = ""


@router.post("/triggers")
async def create_trigger(req: CreateTriggerRequest):
    pool = await get_pg_pool()
    trigger = await EventTriggerService.create_trigger(
        definition_id=req.definition_id,
        trigger_type=req.trigger_type,
        event_pattern=req.event_pattern,
        cron_expression=req.cron_expression,
        condition=req.condition,
        pool=pool,
    )
    return trigger.model_dump()


@router.get("/triggers")
async def list_triggers(definition_id: str | None = None):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if definition_id:
            rows = await conn.fetch("SELECT * FROM workflow_engine.event_triggers WHERE definition_id = $1", definition_id)
        else:
            rows = await conn.fetch("SELECT * FROM workflow_engine.event_triggers")
    return {"triggers": [dict(r) for r in rows]}


@router.put("/triggers/{trigger_id}")
async def update_trigger(trigger_id: str, req: CreateTriggerRequest):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE workflow_engine.event_triggers SET trigger_type=$1, event_pattern=$2, cron_expression=$3, condition=$4 WHERE trigger_id=$5",
            req.trigger_type.value, req.event_pattern, req.cron_expression, req.condition, trigger_id,
        )
    return {"status": "updated"}


@router.delete("/triggers/{trigger_id}")
async def delete_trigger(trigger_id: str):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM workflow_engine.event_triggers WHERE trigger_id = $1", trigger_id)
    return {"status": "deleted"}


@router.post("/triggers/{trigger_id}/test")
async def test_trigger(trigger_id: str):
    pool = await get_pg_pool()
    return await EventTriggerService.test_trigger(trigger_id, pool)