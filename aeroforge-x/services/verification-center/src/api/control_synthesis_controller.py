from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.domain.entities.control_synthesis_result import ControlSynthesisResult
from src.domain.services.control_synthesis_engine import ControlSynthesisEngine

router = APIRouter()
_engine = ControlSynthesisEngine()
_store: dict[str, ControlSynthesisResult] = {}


@router.post("/pid")
async def generate_pid(request: dict[str, Any]):
    result = _engine.generate_pid_control_law(request)
    _store[result.result_id] = result
    return {
        "result_id": result.result_id,
        "pid_params": {"kp": result.pid_params.kp, "ki": result.pid_params.ki, "kd": result.pid_params.kd},
        "stability_margins": {
            "gain_margin_db": result.stability_margins.gain_margin_db,
            "phase_margin_deg": result.stability_margins.phase_margin_deg,
            "is_sufficient": result.stability_margins.is_sufficient,
        },
        "iteration_count": result.iteration_count,
        "status": result.status,
    }


@router.post("/lqr")
async def generate_lqr(request: dict[str, Any]):
    result = _engine.generate_lqr_control_law(request)
    _store[result.result_id] = result
    return {
        "result_id": result.result_id,
        "lqr_params": {
            "state_dimension": result.lqr_params.state_dimension,
            "input_dimension": result.lqr_params.input_dimension,
            "gain_matrix": result.lqr_params.gain_matrix,
        },
        "stability_margins": {
            "gain_margin_db": result.stability_margins.gain_margin_db,
            "phase_margin_deg": result.stability_margins.phase_margin_deg,
            "is_sufficient": result.stability_margins.is_sufficient,
        },
        "status": result.status,
    }


@router.post("/mpc")
async def generate_mpc(request: dict[str, Any]):
    result = _engine.generate_mpc_control_law(request)
    _store[result.result_id] = result
    return {
        "result_id": result.result_id,
        "mpc_params": {
            "prediction_horizon": result.mpc_params.prediction_horizon,
            "control_horizon": result.mpc_params.control_horizon,
            "constraints": result.mpc_params.constraints,
        },
        "stability_margins": {
            "gain_margin_db": result.stability_margins.gain_margin_db,
            "phase_margin_deg": result.stability_margins.phase_margin_deg,
            "is_sufficient": result.stability_margins.is_sufficient,
        },
        "status": result.status,
    }


@router.get("/{result_id}")
async def get_control_synthesis(result_id: str):
    result = _store.get(result_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    return {
        "result_id": result.result_id,
        "control_type": result.control_type,
        "is_margins_satisfied": result.is_margins_satisfied,
        "iteration_count": result.iteration_count,
        "status": result.status,
    }


@router.post("/compare")
async def compare_control_laws(request: dict[str, Any]):
    comparison = _engine.compare_control_law_alternatives(request)
    return comparison