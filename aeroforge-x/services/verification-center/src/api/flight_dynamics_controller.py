from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.domain.entities.flight_dynamics_analysis import FlightDynamicsAnalysis
from src.domain.services.flight_dynamics_engine import FlightDynamicsEngine

router = APIRouter()
_engine = FlightDynamicsEngine()
_store: dict[str, FlightDynamicsAnalysis] = {}


@router.post("/trim")
async def perform_trim(request: dict[str, Any]):
    trim_type = request.get("trim_type", "cruise")
    result = _engine.perform_trim_analysis(request, trim_type)
    return {
        "trim_type": result.trim_type,
        "alpha_deg": result.alpha_deg,
        "elevator_deflection_deg": result.elevator_deflection_deg,
        "throttle_pct": result.throttle_pct,
        "converged": result.converged,
        "iteration_count": result.iteration_count,
    }


@router.post("/simulate-6dof")
async def simulate_6dof(request: dict[str, Any]):
    duration = float(request.get("duration_s", 10.0))
    analysis = FlightDynamicsAnalysis(aircraft_config=request)
    states = _engine.run_6dof_simulation(request, duration_s=duration)
    return {
        "states": [
            {
                "time_s": s.time_s, "phi_deg": s.phi_deg, "theta_deg": s.theta_deg, "psi_deg": s.psi_deg,
                "p_deg_s": s.p_deg_s, "q_deg_s": s.q_deg_s, "r_deg_s": s.r_deg_s,
                "u_m_s": s.u_m_s, "v_m_s": s.v_m_s, "w_m_s": s.w_m_s,
            }
            for s in states
        ],
        "total_steps": len(states),
        "diverged": len(states) < 50 and len(states) > 0,
    }


@router.post("/dynamic-response")
async def analyze_dynamic_response(request: dict[str, Any]):
    response_type = request.get("response_type", "step")
    result = _engine.analyze_dynamic_response(request, response_type)
    return {
        "response_type": result.response_type,
        "settling_time_s": result.settling_time_s,
        "rise_time_s": result.rise_time_s,
        "overshoot_pct": result.overshoot_pct,
        "natural_frequency_hz": result.natural_frequency_hz,
        "damping_ratio": result.damping_ratio,
        "modes": result.modes,
    }


@router.get("/{analysis_id}")
async def get_flight_dynamics_analysis(analysis_id: str):
    analysis = _store.get(analysis_id)
    if not analysis:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
    return {
        "analysis_id": analysis.analysis_id,
        "trim_converged": analysis.trim_converged,
        "simulation_diverged": analysis.simulation_diverged,
        "is_uncontrollable": analysis.is_uncontrollable,
        "status": analysis.status,
    }