from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from src.domain.enums import LifecycleState, ObjectType
from src.domain.services.aircraft_object_service import AircraftObjectService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class CreateObjectRequest(BaseModel):
    object_type: ObjectType
    name: str = Field(..., max_length=200)
    initial_properties: list[dict] | None = None
    parent_object_id: str | None = None


class TransitionRequest(BaseModel):
    target_state: LifecycleState
    force: bool = False
    validation_data: dict[str, bool] | None = None


class UpdateObjectRequest(BaseModel):
    change_summary: str = Field(..., max_length=1000)
    data_updates: dict[str, Any] | None = None
    property_updates: list[dict] | None = None


@router.post("/objects")
async def create_object(req: CreateObjectRequest):
    pool = await get_pg_pool()
    obj = await AircraftObjectService.create_object(
        object_type=req.object_type,
        name=req.name,
        initial_properties=req.initial_properties,
        parent_object_id=req.parent_object_id,
    )
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO aircraft_core.aircraft_objects (id, object_type, name, lifecycle_state, design_data, manufacturing_data, operation_data, certification_data) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            obj.id, obj.object_type.value, obj.name, obj.lifecycle_state.value,
            obj.design_data, obj.manufacturing_data, obj.operation_data, obj.certification_data,
        )
    return obj.model_dump()


@router.get("/objects/{object_id}")
async def get_object(object_id: str):
    pool = await get_pg_pool()
    obj = await AircraftObjectService.get_object_by_id(object_id, pool)
    if obj is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj.model_dump()


@router.get("/objects")
async def list_objects(object_type: str | None = None, lifecycle_state: str | None = None, limit: int = 50, offset: int = 0):
    pool = await get_pg_pool()
    conditions = []
    params = []
    idx = 0
    if object_type:
        idx += 1
        conditions.append(f"object_type = ${idx}")
        params.append(object_type)
    if lifecycle_state:
        idx += 1
        conditions.append(f"lifecycle_state = ${idx}")
        params.append(lifecycle_state)
    where = " AND ".join(conditions) if conditions else "1=1"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM aircraft_core.aircraft_objects WHERE {where} ORDER BY updated_at DESC LIMIT {limit} OFFSET {offset}",
            *params,
        )
    return {"objects": [dict(r) for r in rows], "limit": limit, "offset": offset}


@router.put("/objects/{object_id}")
async def update_object(object_id: str, req: UpdateObjectRequest):
    pool = await get_pg_pool()
    version = await AircraftObjectService.update_object(
        object_id=object_id,
        change_summary=req.change_summary,
        author="system",
        data_updates=req.data_updates,
        pool=pool,
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return version.model_dump()


@router.delete("/objects/{object_id}")
async def delete_object(object_id: str):
    pool = await get_pg_pool()
    deleted = await AircraftObjectService.delete_object(object_id, pool)
    if not deleted:
        raise HTTPException(status_code=404, detail="Object not found")
    return {"status": "deleted"}


@router.post("/objects/{object_id}/transition")
async def transition_lifecycle(object_id: str, req: TransitionRequest):
    pool = await get_pg_pool()
    obj = await AircraftObjectService.transition_lifecycle(
        object_id=object_id,
        target_state=req.target_state,
        validation_data=req.validation_data,
        force=req.force,
        pool=pool,
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj.model_dump()