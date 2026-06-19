from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.plugins.multi_body_dynamics_model import (
    LoadSpectrum,
    MultiBodyDynamicsModel,
)

router = APIRouter(prefix="/api/v4/physics-twin/multi-body-models", tags=["Multi-body Dynamics v4"])

_active_models: dict[str, MultiBodyDynamicsModel] = {}


@router.post("")
async def create_multi_body_model(body: dict[str, Any]):
    mbd_id = body.get("mbd_id", "MBD-001")
    fidelity = body.get("fidelity", "Low")
    params = body.get("params", {})
    params["mbd_id"] = mbd_id
    params["fidelity"] = fidelity

    model = MultiBodyDynamicsModel(fidelity=fidelity)
    model.initialize(params)
    _active_models[mbd_id] = model

    return {
        "mbd_id": mbd_id,
        "fidelity": fidelity,
        "body_count": len(model.bodies),
        "joint_count": len(model.joints),
        "status": "created",
    }


@router.get("/{mbd_id}")
async def get_multi_body_model(mbd_id: str):
    model = _active_models.get(mbd_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{mbd_id}' not found")
    return model.get_state()


@router.post("/{mbd_id}/simulate")
async def simulate_multi_body(mbd_id: str, body: dict[str, Any]):
    model = _active_models.get(mbd_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{mbd_id}' not found")

    dt = body.get("dt", 0.01)
    steps = body.get("steps", 100)
    inputs = body.get("inputs", {})

    results = []
    for _ in range(steps):
        result = model.step(dt, inputs)
        results.append(result)

    return {"mbd_id": mbd_id, "steps": steps, "results": results}


@router.post("/{mbd_id}/flutter-analysis")
async def flutter_analysis(mbd_id: str):
    model = _active_models.get(mbd_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{mbd_id}' not found")

    result = model.compute_flutter_speed()
    return {
        "mbd_id": mbd_id,
        "flutter_speed": result.flutter_speed,
        "flutter_frequency": result.flutter_frequency,
        "is_stable": result.is_stable,
        "method": result.method,
    }


@router.post("/{mbd_id}/divergence-analysis")
async def divergence_analysis(mbd_id: str):
    model = _active_models.get(mbd_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{mbd_id}' not found")

    result = model.compute_divergence_speed()
    return {
        "mbd_id": mbd_id,
        "divergence_speed": result.divergence_speed,
        "is_divergent": result.is_divergent,
        "critical_mode": result.critical_mode,
    }


@router.post("/{mbd_id}/fatigue-prediction")
async def fatigue_prediction(mbd_id: str, body: dict[str, Any]):
    model = _active_models.get(mbd_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model '{mbd_id}' not found")

    spectrum = LoadSpectrum(
        stress_amplitudes=body.get("stress_amplitudes", []),
        cycle_counts=body.get("cycle_counts", []),
    )
    material_id = body.get("material_id", "default")

    result = model.predict_fatigue_life(spectrum, material_id)
    return {
        "mbd_id": mbd_id,
        "cumulative_damage": result.cumulative_damage,
        "remaining_life_ratio": result.remaining_life_ratio,
        "is_failed": result.is_failed,
        "confidence": result.confidence,
    }