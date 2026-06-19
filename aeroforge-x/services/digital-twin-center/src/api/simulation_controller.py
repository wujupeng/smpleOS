from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.simulation_models import FlightState
from ..domain.services.realtime_simulation_service import RealtimeSimulationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/twins", tags=["Realtime Simulation"])

_service = RealtimeSimulationService()


class SetupModelRequest(BaseModel):
    aircraft_sn: str = Field(..., min_length=1)
    structural_params: dict[str, float] | None = None
    aero_params: dict[str, float] | None = None


class FlightStateRequest(BaseModel):
    altitude_m: float = 0.0
    airspeed_ms: float = 0.0
    heading_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    vertical_speed_ms: float = 0.0
    g_load: float = 1.0
    engine_rpm: float = 0.0
    fuel_kg: float = 0.0
    temperature_c: float = 20.0


class RunSimulationRequest(BaseModel):
    aircraft_sn: str = Field(..., min_length=1)
    current_state: FlightStateRequest | None = None
    dt_seconds: float = 0.1


class CompareRequest(BaseModel):
    aircraft_sn: str = Field(..., min_length=1)
    actual_state: FlightStateRequest


@router.post("/simulation/setup", response_model=ApiResponse[dict])
async def setup_model(body: SetupModelRequest):
    model = _service.setup_simulation_model(
        aircraft_sn=body.aircraft_sn,
        structural_params=body.structural_params,
        aero_params=body.aero_params,
    )
    return ApiResponse(data=model.to_dict())


@router.post("/{aircraft_sn}/simulation/start", response_model=ApiResponse[dict])
async def start_simulation(aircraft_sn: str):
    success = _service.start_simulation(aircraft_sn)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation model not found")
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "status": "running"})


@router.post("/{aircraft_sn}/simulation/stop", response_model=ApiResponse[dict])
async def stop_simulation(aircraft_sn: str):
    success = _service.stop_simulation(aircraft_sn)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation model not found")
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "status": "stopped"})


@router.get("/{aircraft_sn}/simulation/status", response_model=ApiResponse[dict])
async def get_simulation_status(aircraft_sn: str):
    status = _service.get_simulation_status(aircraft_sn)
    if status is None:
        raise HTTPException(status_code=404, detail="Simulation model not found")
    return ApiResponse(data=status)


@router.post("/simulation/step", response_model=ApiResponse[dict])
async def run_simulation_step(body: RunSimulationRequest):
    current_state = None
    if body.current_state:
        current_state = FlightState(**body.current_state.model_dump())

    result = _service.run_realtime_simulation(
        aircraft_sn=body.aircraft_sn,
        current_state=current_state,
        dt_seconds=body.dt_seconds,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation not running or model not found")
    return ApiResponse(data=result.to_dict())


@router.post("/simulation/compare", response_model=ApiResponse[dict])
async def compare_actual_vs_predicted(body: CompareRequest):
    actual = FlightState(**body.actual_state.model_dump())
    result = _service.compare_actual_vs_predicted(body.aircraft_sn, actual)
    if result is None:
        raise HTTPException(status_code=404, detail="No simulation results found")
    return ApiResponse(data=result)


@router.post("/{aircraft_sn}/simulation/calibrate", response_model=ApiResponse[dict])
async def calibrate_model(aircraft_sn: str):
    result = _service.calibrate_model(aircraft_sn)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation model not found")
    return ApiResponse(data=result.to_dict())


@router.get("/{aircraft_sn}/simulation/results", response_model=ApiResponse[dict])
async def get_simulation_results(aircraft_sn: str, limit: int = 20):
    results = _service.get_results(aircraft_sn, limit)
    return ApiResponse(data={
        "total": len(results),
        "results": [r.to_dict() for r in results],
    })