from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.plugins.pack_battery_model import PackBatteryModel

router = APIRouter(prefix="/api/v4/physics-twin/battery-packs", tags=["Pack Battery v4"])

_active_packs: dict[str, PackBatteryModel] = {}


@router.post("")
async def create_battery_pack(body: dict[str, Any]):
    pack_id = body.get("pack_id", "PAK-001")
    fidelity = body.get("fidelity", "Low")
    params = body.get("params", {})
    params["pack_id"] = pack_id
    params["fidelity"] = fidelity

    pack = PackBatteryModel(fidelity=fidelity)
    pack.initialize(params)
    _active_packs[pack_id] = pack

    return {
        "pack_id": pack_id,
        "fidelity": fidelity,
        "status": "created",
        "series_count": pack.series_count,
        "parallel_count": pack.parallel_count,
        "module_count": len(pack.modules),
    }


@router.get("/{pack_id}")
async def get_battery_pack(pack_id: str):
    pack = _active_packs.get(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")
    return pack.get_state()


@router.post("/{pack_id}/simulate")
async def simulate_battery_pack(pack_id: str, body: dict[str, Any]):
    pack = _active_packs.get(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    dt = body.get("dt", 1.0)
    steps = body.get("steps", 100)
    inputs = body.get("inputs", {})

    results = []
    for _ in range(steps):
        result = pack.step(dt, inputs)
        results.append(result)

    return {"pack_id": pack_id, "steps": steps, "results": results}


@router.post("/{pack_id}/thermal-runaway")
async def simulate_thermal_runaway(pack_id: str, body: dict[str, Any]):
    pack = _active_packs.get(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    event = pack.check_thermal_runaway()
    if event is None:
        return {"status": "no_runaway", "message": "No thermal runaway detected"}
    return {
        "status": "runaway_detected",
        "trigger_cell": event.trigger_cell_id,
        "propagation_path": event.propagation_path,
        "estimated_full_propagation_time_s": event.estimated_full_propagation_time,
        "safety_recommendation": event.safety_recommendation,
    }


@router.get("/{pack_id}/bms-status")
async def get_bms_status(pack_id: str):
    pack = _active_packs.get(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    return {
        "pack_id": pack_id,
        "bms_status": pack._pack_state.bms_status,
        "ovp_threshold": pack.bms_simulator.ovp_threshold,
        "uvp_threshold": pack.bms_simulator.uvp_threshold,
        "ocp_threshold": pack.bms_simulator.ocp_threshold,
        "otp_threshold": pack.bms_simulator.otp_threshold,
        "balancing_mode": pack.bms_simulator.balancing_mode,
        "isolated_modules": pack._pack_state.isolated_modules,
    }