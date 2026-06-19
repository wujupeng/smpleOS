from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.generative_design.parametric_geometry_service import (
    ParametricGeometryService,
    DesignParameters,
)

router = APIRouter(prefix="/api/v5/physics-twin/aircraft-geometries", tags=["Parametric Geometry v5"])

_service = ParametricGeometryService()


@router.post("")
async def generate_geometry(body: dict[str, Any]):
    try:
        params = DesignParameters(
            wing_span=body["wing_span"],
            wing_area=body["wing_area"],
            wing_aspect_ratio=body["wing_aspect_ratio"],
            wing_sweep_angle=body["wing_sweep_angle"],
            wing_taper_ratio=body["wing_taper_ratio"],
            fuselage_length=body["fuselage_length"],
            fuselage_diameter=body["fuselage_diameter"],
            horizontal_tail_area=body.get("horizontal_tail_area"),
            vertical_tail_area=body.get("vertical_tail_area"),
            engine_count=body.get("engine_count", 2),
            engine_thrust=body.get("engine_thrust", 25000.0),
        )
    except (KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Missing required parameter: {e}")

    requirement_id = body.get("requirement_id")
    geometry = _service.generate_geometry(parameters=params, requirement_id=requirement_id)
    return geometry.to_dict()


@router.put("/{geometry_id}/regenerate")
async def regenerate_geometry(geometry_id: str, body: dict[str, Any]):
    try:
        params = DesignParameters(
            wing_span=body["wing_span"],
            wing_area=body["wing_area"],
            wing_aspect_ratio=body["wing_aspect_ratio"],
            wing_sweep_angle=body["wing_sweep_angle"],
            wing_taper_ratio=body["wing_taper_ratio"],
            fuselage_length=body["fuselage_length"],
            fuselage_diameter=body["fuselage_diameter"],
            horizontal_tail_area=body.get("horizontal_tail_area"),
            vertical_tail_area=body.get("vertical_tail_area"),
            engine_count=body.get("engine_count", 2),
            engine_thrust=body.get("engine_thrust", 25000.0),
        )
    except (KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Missing required parameter: {e}")

    try:
        geometry = _service.regenerate_geometry(geometry_id=geometry_id, parameters=params)
        return geometry.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{geometry_id}/export")
async def export_geometry(geometry_id: str, body: dict[str, Any]):
    format = body.get("format", "STEP")
    try:
        path = _service.export_geometry(geometry_id=geometry_id, format=format)
        return {"geometry_id": geometry_id, "format": format, "path": path}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{geometry_id}/validate-manufacturing")
async def validate_manufacturing(geometry_id: str):
    geometry = _service.get_geometry(geometry_id)
    if geometry is None:
        raise HTTPException(status_code=404, detail="Geometry not found")

    result = _service.validate_manufacturing_constraints(geometry)
    return {
        "geometry_id": geometry_id,
        "passed": result.passed,
        "violations": [
            {
                "violation_type": v.violation_type,
                "parameter": v.parameter,
                "current_value": v.current_value,
                "required_value": v.required_value,
                "message": v.message,
            }
            for v in result.violations
        ],
        "nearest_feasible_geometry": result.nearest_feasible_geometry,
    }