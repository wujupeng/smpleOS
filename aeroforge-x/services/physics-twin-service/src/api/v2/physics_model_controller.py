from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from src.domain.enums import FidelityLevel, HierarchyLevel, PhysicsType
from src.domain.services.physics_model_service import PhysicsModelService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class CreateModelRequest(BaseModel):
    name: str
    model_type: PhysicsType
    hierarchy_level: HierarchyLevel
    fidelity_level: FidelityLevel
    aircraft_object_id: str
    parameter_mappings: list[dict] | None = None


class SwitchFidelityRequest(BaseModel):
    fidelity_level: FidelityLevel


class MapParametersRequest(BaseModel):
    parameter_mappings: list[dict]


@router.post("/models")
async def create_model(req: CreateModelRequest):
    pool = await get_pg_pool()
    try:
        model = await PhysicsModelService.create_model(
            name=req.name, model_type=req.model_type, hierarchy_level=req.hierarchy_level,
            fidelity_level=req.fidelity_level, aircraft_object_id=req.aircraft_object_id,
            parameter_mappings=req.parameter_mappings, pool=pool,
        )
        return model.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models")
async def list_models(aircraft_object_id: str | None = None):
    pool = await get_pg_pool()
    models = await PhysicsModelService.list_models(aircraft_object_id=aircraft_object_id, pool=pool)
    return {"models": models}


@router.get("/models/{model_id}")
async def get_model(model_id: str):
    pool = await get_pg_pool()
    model = await PhysicsModelService.get_model(model_id, pool)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return model.model_dump()


@router.put("/models/{model_id}")
async def update_model(model_id: str, name: str | None = None, parameter_mappings: list[dict] | None = None):
    pool = await get_pg_pool()
    kwargs = {}
    if name:
        kwargs["name"] = name
    if parameter_mappings:
        kwargs["parameter_mappings"] = parameter_mappings
    result = await PhysicsModelService.update_model(model_id, pool=pool, **kwargs)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/models/{model_id}/switch-fidelity")
async def switch_fidelity(model_id: str, req: SwitchFidelityRequest):
    pool = await get_pg_pool()
    model = await PhysicsModelService.switch_fidelity(model_id, req.fidelity_level, pool)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return model.model_dump()


@router.post("/models/{model_id}/map-parameters")
async def map_parameters(model_id: str, req: MapParametersRequest):
    pool = await get_pg_pool()
    return await PhysicsModelService.map_parameters(model_id, req.parameter_mappings, pool)