from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from src.domain.enums import DataType, PropertyType, SourceTag
from src.domain.services.property_service import PropertyService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class CreatePropertyDefRequest(BaseModel):
    name: str
    property_type: PropertyType
    data_type: DataType
    unit: str
    constraints: dict[str, Any] | None = None
    applicable_object_types: list[str] | None = None
    derivation_formula: str | None = None


class SetPropertyValueRequest(BaseModel):
    property_def_id: str
    value: Any
    source: SourceTag = SourceTag.DesignValue
    source_detail: str = ""
    confidence: float = 1.0
    version_id: str = ""


class UnitConvertRequest(BaseModel):
    value: float
    from_unit: str
    to_unit: str


@router.post("/property-definitions")
async def create_property_definition(req: CreatePropertyDefRequest):
    pool = await get_pg_pool()
    prop_def = await PropertyService.create_property_definition(
        name=req.name,
        property_type=req.property_type,
        data_type=req.data_type,
        unit=req.unit,
        constraints=req.constraints,
        applicable_object_types=req.applicable_object_types,
        derivation_formula=req.derivation_formula,
        pool=pool,
    )
    return prop_def.model_dump()


@router.get("/property-definitions")
async def list_property_definitions(property_type: str | None = None):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if property_type:
            rows = await conn.fetch(
                "SELECT * FROM aircraft_core.property_definitions WHERE property_type = $1", property_type
            )
        else:
            rows = await conn.fetch("SELECT * FROM aircraft_core.property_definitions")
    return {"definitions": [dict(r) for r in rows]}


@router.put("/property-definitions/{prop_def_id}")
async def update_property_definition(prop_def_id: str, req: CreatePropertyDefRequest):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE aircraft_core.property_definitions SET name=$1, property_type=$2, data_type=$3, unit=$4, constraints=$5, derivation_formula=$6, updated_at=NOW() WHERE id=$7",
            req.name, req.property_type.value, req.data_type.value, req.unit,
            req.constraints or {}, req.derivation_formula, prop_def_id,
        )
    return {"status": "updated"}


@router.post("/objects/{object_id}/properties")
async def set_property_value(object_id: str, req: SetPropertyValueRequest):
    pool = await get_pg_pool()
    try:
        prop = await PropertyService.set_property_value(
            object_id=object_id,
            property_def_id=req.property_def_id,
            value=req.value,
            source=req.source,
            source_detail=req.source_detail,
            confidence=req.confidence,
            version_id=req.version_id,
            pool=pool,
        )
        return prop.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/objects/{object_id}/properties")
async def get_object_properties(object_id: str, property_type: str | None = None):
    pool = await get_pg_pool()
    pt = PropertyType(property_type) if property_type else None
    props = await PropertyService.get_object_properties(object_id, property_type=pt, pool=pool)
    return {"properties": [p.model_dump() for p in props]}


@router.post("/properties/convert-unit")
async def convert_unit(req: UnitConvertRequest):
    try:
        result = PropertyService.convert_unit(req.value, req.from_unit, req.to_unit)
        return {"original_value": req.value, "original_unit": req.from_unit, "converted_value": result, "target_unit": req.to_unit}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))