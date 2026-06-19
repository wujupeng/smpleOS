from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.entities.aircraft_spec import AircraftSpec, SpecParameter
from src.domain.entities.requirement_trace import RequirementTrace
from src.domain.services.spec_service import SpecService
from src.domain.services.requirement_trace_service import RequirementTraceService
from src.domain.services.sensitivity_analysis_service import SensitivityAnalysisService
from src.domain.value_objects.enums import (
    AircraftType,
    PowerType,
    SpecStatus,
    ParameterCategory,
    ParameterPriority,
    TraceType,
    TraceSourceType,
)

router = APIRouter()

spec_service = SpecService()
trace_service = RequirementTraceService()
sensitivity_service = SensitivityAnalysisService()

_specs_store: dict[str, AircraftSpec] = {}


def _spec_to_dict(spec: AircraftSpec) -> dict[str, Any]:
    return {
        "spec_id": spec.spec_id,
        "spec_number": spec.spec_number,
        "aircraft_type": spec.aircraft_type.value,
        "version": spec.version,
        "status": spec.status.value,
        "payload_kg": float(spec.payload_kg) if spec.payload_kg else None,
        "range_km": float(spec.range_km) if spec.range_km else None,
        "cruise_speed_kmh": float(spec.cruise_speed_kmh) if spec.cruise_speed_kmh else None,
        "takeoff_distance_m": float(spec.takeoff_distance_m) if spec.takeoff_distance_m else None,
        "power_type": spec.power_type.value if spec.power_type else None,
        "budget_cny": float(spec.budget_cny) if spec.budget_cny else None,
        "material_id": spec.material_id,
        "certification_level_id": spec.certification_level_id,
        "derived_constraints": spec.derived_constraints,
        "parameters": [
            {
                "parameter_id": p.parameter_id,
                "name": p.name,
                "category": p.category.value,
                "value": float(p.value) if p.value else None,
                "unit": p.unit,
                "tolerance": float(p.tolerance) if p.tolerance else None,
                "priority": p.priority.value,
                "is_required": p.is_required,
            }
            for p in spec.parameters
        ],
        "created_by": spec.created_by,
        "approved_by": spec.approved_by,
        "confirmed_at": spec.confirmed_at.isoformat() if spec.confirmed_at else None,
        "frozen_at": spec.frozen_at.isoformat() if spec.frozen_at else None,
        "created_at": spec.created_at.isoformat(),
        "updated_at": spec.updated_at.isoformat(),
    }


@router.post("/specs")
async def create_spec(request: dict[str, Any]):
    aircraft_type = AircraftType(request.get("aircraft_type", "fixed_wing"))
    power_type = PowerType(request["power_type"]) if request.get("power_type") else None
    spec = spec_service.create_spec(
        aircraft_type=aircraft_type,
        created_by=request.get("created_by"),
        payload_kg=Decimal(str(request["payload_kg"])) if request.get("payload_kg") else None,
        range_km=Decimal(str(request["range_km"])) if request.get("range_km") else None,
        cruise_speed_kmh=Decimal(str(request["cruise_speed_kmh"])) if request.get("cruise_speed_kmh") else None,
        takeoff_distance_m=Decimal(str(request["takeoff_distance_m"])) if request.get("takeoff_distance_m") else None,
        power_type=power_type,
        budget_cny=Decimal(str(request["budget_cny"])) if request.get("budget_cny") else None,
    )
    if request.get("parameters"):
        for p in request["parameters"]:
            param = SpecParameter(
                name=p["name"],
                category=ParameterCategory(p.get("category", "performance")),
                value=Decimal(str(p["value"])) if p.get("value") is not None else None,
                unit=p.get("unit", ""),
                tolerance=Decimal(str(p["tolerance"])) if p.get("tolerance") else None,
                priority=ParameterPriority(p.get("priority", "medium")),
                is_required=p.get("is_required", False),
                validation_rules=p.get("validation_rules", []),
            )
            spec.add_parameter(param)
    constraints = spec_service.derive_constraints(spec)
    spec.derived_constraints = constraints
    _specs_store[spec.spec_id] = spec
    return _spec_to_dict(spec)


@router.get("/specs/{spec_id}")
async def get_spec(spec_id: str):
    spec = _specs_store.get(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec {spec_id} not found")
    return _spec_to_dict(spec)


@router.put("/specs/{spec_id}")
async def update_spec(spec_id: str, request: dict[str, Any]):
    spec = _specs_store.get(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec {spec_id} not found")
    spec.update_parameters(
        payload_kg=Decimal(str(request["payload_kg"])) if request.get("payload_kg") else None,
        range_km=Decimal(str(request["range_km"])) if request.get("range_km") else None,
        cruise_speed_kmh=Decimal(str(request["cruise_speed_kmh"])) if request.get("cruise_speed_kmh") else None,
        takeoff_distance_m=Decimal(str(request["takeoff_distance_m"])) if request.get("takeoff_distance_m") else None,
        power_type=PowerType(request["power_type"]) if request.get("power_type") else None,
        budget_cny=Decimal(str(request["budget_cny"])) if request.get("budget_cny") else None,
    )
    constraints = spec_service.derive_constraints(spec)
    spec.derived_constraints = constraints
    return _spec_to_dict(spec)


@router.post("/specs/{spec_id}/validate")
async def validate_spec(spec_id: str):
    spec = _specs_store.get(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec {spec_id} not found")
    violations = spec_service.validate_spec(spec)
    return {"spec_id": spec_id, "violations": violations, "is_valid": len([v for v in violations if v["severity"] == "error"]) == 0}


@router.post("/specs/{spec_id}/confirm")
async def confirm_spec(spec_id: str):
    spec = _specs_store.get(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Spec {spec_id} not found")
    try:
        spec_service.confirm_spec(spec)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    events = spec.clear_events()
    return {**_spec_to_dict(spec), "events": events}


@router.get("/specs/{spec_id}/traces")
async def get_spec_traces(spec_id: str):
    traces = trace_service.get_traces_for_source(TraceSourceType.SPEC, spec_id)
    chain = trace_service.get_trace_chain(spec_id)
    return {
        "spec_id": spec_id,
        "traces": [
            {
                "trace_id": t.trace_id,
                "source_type": t.source_type.value,
                "source_id": t.source_id,
                "target_type": t.target_type.value,
                "target_id": t.target_id,
                "trace_type": t.trace_type.value,
                "confidence": float(t.confidence),
            }
            for t in traces
        ],
        "trace_chain": [
            {
                "trace_id": t.trace_id,
                "source_type": t.source_type.value,
                "source_id": t.source_id,
                "target_type": t.target_type.value,
                "target_id": t.target_id,
                "trace_type": t.trace_type.value,
            }
            for t in chain
        ],
    }


@router.post("/sensitivity")
async def run_sensitivity(request: dict[str, Any]):
    spec_id = request.get("spec_id")
    if not spec_id or spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")
    spec = _specs_store[spec_id]
    parameters = request.get("parameters")
    perturbation_pct = request.get("perturbation_pct", 0.05)
    results = sensitivity_service.run_sensitivity_analysis(spec, parameters, perturbation_pct)
    return {
        "spec_id": spec_id,
        "perturbation_pct": perturbation_pct,
        "results": [
            {
                "parameter_name": r.parameter_name,
                "baseline_value": float(r.baseline_value) if r.baseline_value else None,
                "perturbation": float(r.perturbation),
                "sensitivity_index": r.sensitivity_index,
                "influence_rank": r.influence_rank,
                "performance_impact": r.performance_impact,
            }
            for r in results
        ],
    }