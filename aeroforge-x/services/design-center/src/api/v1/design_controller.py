from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.entities.v1.parametric_model import ParametricModel, ModelType
from src.domain.entities.v1.airframe_model import AirframeModel
from src.domain.entities.v1.structure_model import StructureModel
from src.domain.entities.v1.powertrain_model import PowertrainModel
from src.domain.entities.v1.wire_harness_model import WireHarnessModel
from src.domain.services.v1.param_model_service import ParamModelService
from src.domain.services.v1.design_rule_engine_v1 import DesignRuleEngineV1
from src.domain.services.v1.airframe_gen_service import AirframeGenService
from src.domain.services.v1.structure_gen_service import StructureGenService
from src.domain.services.v1.powertrain_service import PowertrainService
from src.domain.services.v1.wire_harness_service import WireHarnessService

router = APIRouter()

param_model_service = ParamModelService()
rule_engine = DesignRuleEngineV1()
airframe_gen_service = AirframeGenService()
structure_gen_service = StructureGenService()
powertrain_service = PowertrainService()
wire_harness_service = WireHarnessService()

_models_store: dict[str, ParametricModel] = {}
_airframes_store: dict[str, AirframeModel] = {}
_structures_store: dict[str, list[StructureModel]] = {}
_powertrains_store: dict[str, PowertrainModel] = {}
_harnesses_store: dict[str, WireHarnessModel] = {}


def _model_to_dict(model: ParametricModel) -> dict[str, Any]:
    return {
        "model_id": model.model_id,
        "spec_ref": model.spec_ref,
        "model_name": model.model_name,
        "model_type": model.model_type.value,
        "parameters": model.parameters,
        "constraints": model.constraints,
        "version": model.version,
        "status": model.status.value,
        "geometry_data": model.geometry_data,
        "created_by": model.created_by,
        "created_at": model.created_at.isoformat(),
        "updated_at": model.updated_at.isoformat(),
    }


def _airframe_to_dict(af: AirframeModel) -> dict[str, Any]:
    return {
        "airframe_id": af.airframe_id,
        "model_ref": af.model_ref,
        "fuselage_params": {
            "length_m": af.fuselage_params.length_m,
            "diameter_m": af.fuselage_params.diameter_m,
            "fineness_ratio": af.fuselage_params.fineness_ratio,
            "nose_cone_ratio": af.fuselage_params.nose_cone_ratio,
            "tail_cone_ratio": af.fuselage_params.tail_cone_ratio,
        },
        "wing_params": {
            "span_m": af.wing_params.span_m,
            "aspect_ratio": af.wing_params.aspect_ratio,
            "area_m2": af.wing_params.area_m2,
            "taper_ratio": af.wing_params.taper_ratio,
            "sweep_angle_deg": af.wing_params.sweep_angle_deg,
            "root_chord_m": af.wing_params.root_chord_m,
            "tip_chord_m": af.wing_params.tip_chord_m,
            "incidence_angle_deg": af.wing_params.incidence_angle_deg,
            "dihedral_angle_deg": af.wing_params.dihedral_angle_deg,
        },
        "tail_params": {
            "h_tail_area_m2": af.tail_params.h_tail_area_m2,
            "h_tail_arm_m": af.tail_params.h_tail_arm_m,
            "v_tail_area_m2": af.tail_params.v_tail_area_m2,
            "v_tail_arm_m": af.tail_params.v_tail_arm_m,
        },
        "landing_gear_params": {
            "type": af.landing_gear_params.type_,
            "main_gear_position": af.landing_gear_params.main_gear_position,
            "wheel_track_m": af.landing_gear_params.wheel_track_m,
            "wheel_base_m": af.landing_gear_params.wheel_base_m,
        },
        "status": af.status.value,
    }


@router.post("/models")
async def create_model(request: dict[str, Any]):
    model_type = ModelType(request.get("model_type", "full_assembly"))
    model = param_model_service.generate_model(request, model_type)
    _models_store[model.model_id] = model
    return _model_to_dict(model)


@router.get("/models/{model_id}")
async def get_model(model_id: str):
    model = _models_store.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return _model_to_dict(model)


@router.put("/models/{model_id}")
async def update_model(model_id: str, request: dict[str, Any]):
    model = _models_store.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    param_model_service.update_model(model, request.get("parameters", {}))
    return _model_to_dict(model)


@router.post("/models/{model_id}/validate")
async def validate_model(model_id: str, request: dict[str, Any] | None = None):
    model = _models_store.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    domain = request.get("domain") if request else None
    violations = rule_engine.validate(model.parameters, domain)
    return {
        "model_id": model_id,
        "violations": [
            {"rule_id": v.rule_id, "severity": v.severity.value, "message": v.message, "suggestion": v.suggestion}
            for v in violations
        ],
        "is_valid": len([v for v in violations if v.severity.value in ("error", "critical")]) == 0,
    }


@router.post("/airframe/generate")
async def generate_airframe(request: dict[str, Any]):
    airframe = airframe_gen_service.generate_airframe(request)
    _airframes_store[airframe.airframe_id] = airframe
    return _airframe_to_dict(airframe)


@router.post("/structure/generate")
async def generate_structure(request: dict[str, Any]):
    structures = structure_gen_service.generate_structure(request)
    result_id = structures[0].structure_id if structures else "none"
    _structures_store[result_id] = structures
    return {
        "structures": [
            {
                "structure_id": s.structure_id,
                "component_type": s.component_type.value,
                "material": s.material,
                "geometry": s.geometry,
                "status": s.status.value,
            }
            for s in structures
        ],
        "total_count": len(structures),
    }


@router.post("/powertrain/generate")
async def generate_powertrain(request: dict[str, Any]):
    powertrain = powertrain_service.generate_powertrain(request)
    _powertrains_store[powertrain.powertrain_id] = powertrain
    return {
        "powertrain_id": powertrain.powertrain_id,
        "motor_spec": {
            "motor_type": powertrain.motor_spec.motor_type,
            "max_thrust_n": powertrain.motor_spec.max_thrust_n,
            "kv_rating": powertrain.motor_spec.kv_rating,
            "weight_kg": powertrain.motor_spec.weight_kg,
            "efficiency_pct": powertrain.motor_spec.efficiency_pct,
        },
        "battery_spec": {
            "chemistry": powertrain.battery_spec.chemistry,
            "capacity_mah": powertrain.battery_spec.capacity_mah,
            "cell_count": powertrain.battery_spec.cell_count,
            "voltage_v": powertrain.battery_spec.voltage_v,
            "max_discharge_c": powertrain.battery_spec.max_discharge_c,
            "weight_kg": powertrain.battery_spec.weight_kg,
        },
        "esc_spec": {
            "max_current_a": powertrain.esc_spec.max_current_a,
            "weight_kg": powertrain.esc_spec.weight_kg,
            "protocol": powertrain.esc_spec.protocol,
        },
        "thrust_params": powertrain.thrust_params,
        "propeller_params": powertrain.propeller_params,
        "status": powertrain.status.value,
    }


@router.post("/wire-harness/generate")
async def generate_wire_harness(request: dict[str, Any]):
    powertrain_params = request.get("powertrain_params")
    harness = wire_harness_service.generate_wire_harness(request, powertrain_params)
    _harnesses_store[harness.harness_id] = harness
    return {
        "harness_id": harness.harness_id,
        "harness_type": harness.harness_type.value,
        "wire_count": len(harness.wire_list),
        "connector_count": len(harness.connector_list),
        "routing_path_count": len(harness.routing_paths),
        "total_weight_kg": round(harness.calculate_total_weight(), 4),
        "status": harness.status.value,
    }