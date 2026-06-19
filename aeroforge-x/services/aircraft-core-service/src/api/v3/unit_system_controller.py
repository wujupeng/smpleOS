from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.domain.services.unit_conversion_service import UnitConversionService

router = APIRouter(prefix="/api/v3/aircraft-core/units", tags=["Unit System v3"])


@router.post("/convert")
async def convert_unit(body: dict[str, Any]):
    value = body.get("value", 0)
    from_unit = body.get("from_unit", "")
    to_unit = body.get("to_unit", "")
    try:
        result = UnitConversionService.convert_unit(value, from_unit, to_unit)
        return {"value": result, "from_unit": from_unit, "to_unit": to_unit}
    except ValueError as e:
        return {"error": str(e)}


@router.get("/supported")
async def get_supported_units():
    return UnitConversionService.get_supported_units()


@router.post("/validate-dimension")
async def validate_dimensional_compatibility(body: dict[str, Any]):
    unit1 = body.get("unit1", "")
    unit2 = body.get("unit2", "")
    compatible = UnitConversionService.validate_dimensional_compatibility(unit1, unit2)
    return {"unit1": unit1, "unit2": unit2, "compatible": compatible}