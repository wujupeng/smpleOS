from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.plugins.flight_mode_manager import FlightMode, FlightModeManager

router = APIRouter(prefix="/api/v4/physics-twin/flight-mode-managers", tags=["Flight Mode Manager v4"])

_active_managers: dict[str, FlightModeManager] = {}


@router.post("")
async def create_flight_mode_manager(body: dict[str, Any]):
    fmm_id = body.get("fmm_id", "FMM-001")
    fidelity = body.get("fidelity", "Low")
    params = body.get("params", {})
    params["fmm_id"] = fmm_id
    params["fidelity"] = fidelity

    mgr = FlightModeManager(fidelity=fidelity)
    mgr.initialize(params)
    _active_managers[fmm_id] = mgr

    return {
        "fmm_id": fmm_id,
        "fidelity": fidelity,
        "current_mode": mgr.get_current_mode().value,
        "status": "created",
    }


@router.get("/{fmm_id}")
async def get_flight_mode_manager(fmm_id: str):
    mgr = _active_managers.get(fmm_id)
    if mgr is None:
        raise HTTPException(status_code=404, detail=f"FMM '{fmm_id}' not found")
    return mgr.get_state()


@router.post("/{fmm_id}/transition")
async def request_mode_transition(fmm_id: str, body: dict[str, Any]):
    mgr = _active_managers.get(fmm_id)
    if mgr is None:
        raise HTTPException(status_code=404, detail=f"FMM '{fmm_id}' not found")

    target_mode_str = body.get("target_mode", "")
    try:
        target_mode = FlightMode(target_mode_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {target_mode_str}")

    flight_state = body.get("flight_state", {})
    result = mgr.request_mode_transition(target_mode, flight_state)

    if not result.success:
        return {"success": False, "message": result.message, "from_mode": result.from_mode.value, "to_mode": result.to_mode.value}

    return {
        "success": True,
        "from_mode": result.from_mode.value,
        "to_mode": result.to_mode.value,
        "is_emergency": result.is_emergency,
        "message": result.message,
    }


@router.post("/{fmm_id}/emergency-override")
async def emergency_override(fmm_id: str):
    mgr = _active_managers.get(fmm_id)
    if mgr is None:
        raise HTTPException(status_code=404, detail=f"FMM '{fmm_id}' not found")

    result = mgr.emergency_override()
    return {
        "success": result.success,
        "from_mode": result.from_mode.value,
        "to_mode": result.to_mode.value,
        "is_emergency": result.is_emergency,
        "message": result.message,
    }


@router.get("/{fmm_id}/control-law")
async def get_control_law(fmm_id: str):
    mgr = _active_managers.get(fmm_id)
    if mgr is None:
        raise HTTPException(status_code=404, detail=f"FMM '{fmm_id}' not found")

    cl = mgr.get_control_law_params()
    return {
        "fmm_id": fmm_id,
        "current_mode": mgr.get_current_mode().value,
        "control_law": {
            "pid_kp": cl.pid_kp,
            "pid_ki": cl.pid_ki,
            "pid_kd": cl.pid_kd,
            "sas_pitch_gain": cl.sas_pitch_gain,
            "sas_roll_gain": cl.sas_roll_gain,
            "sas_yaw_gain": cl.sas_yaw_gain,
            "autopilot_sub_mode": cl.autopilot_sub_mode.value,
        },
    }


@router.get("/{fmm_id}/history")
async def get_transition_history(fmm_id: str):
    mgr = _active_managers.get(fmm_id)
    if mgr is None:
        raise HTTPException(status_code=404, detail=f"FMM '{fmm_id}' not found")

    history = [
        {
            "from_mode": r.from_mode.value,
            "to_mode": r.to_mode.value,
            "timestamp": r.timestamp,
            "transition_type": r.transition_type,
            "is_rejected": r.is_rejected,
            "rejection_reason": r.rejection_reason,
        }
        for r in mgr.fsm.mode_history
    ]
    return {"fmm_id": fmm_id, "history": history}