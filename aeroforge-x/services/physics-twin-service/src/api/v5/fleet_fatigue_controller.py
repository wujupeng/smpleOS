from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.domain.services.fleet_intelligence.fleet_fatigue_tracker_service import (
    FleetFatigueTrackerService,
    FlightLoadData,
)

router = APIRouter(prefix="/api/v5/physics-twin/fleet/fatigue", tags=["Fleet Fatigue v5"])

_service = FleetFatigueTrackerService()


@router.post("/update")
async def update_fatigue_damage(body: dict[str, Any]):
    flight_data = FlightLoadData(
        flight_id=body.get("flight_id", ""),
        aircraft_id=body.get("aircraft_id", ""),
        flight_hours=body.get("flight_hours", 0.0),
        load_factor_spectrum=body.get("load_factor_spectrum", []),
        max_load_factor=body.get("max_load_factor", 1.0),
        min_load_factor=body.get("min_load_factor", 0.5),
        gust_load_cycles=body.get("gust_load_cycles", 0),
        maneuver_load_cycles=body.get("maneuver_load_cycles", 0),
    )
    result = _service.update_fatigue_damage(flight_data=flight_data)
    return {
        "aircraft_id": result.aircraft_id,
        "cumulative_damage": result.cumulative_damage,
        "remaining_fatigue_life_hours": result.remaining_fatigue_life_hours,
        "consumption_rate_per_flight_hour": result.consumption_rate_per_flight_hour,
        "is_warning": result.is_warning,
        "critical_locations": result.critical_locations,
    }


@router.post("/distribution")
async def get_fleet_fatigue_distribution():
    result = _service.get_fleet_fatigue_distribution()
    return {
        "total_aircraft": result.total_aircraft,
        "p10_remaining_hours": result.p10_remaining_hours,
        "p50_remaining_hours": result.p50_remaining_hours,
        "p90_remaining_hours": result.p90_remaining_hours,
        "avg_cumulative_damage": result.avg_cumulative_damage,
        "warning_count": result.warning_count,
    }


@router.get("/{aircraft_id}/correlation")
async def correlate_fatigue_with_operations(aircraft_id: str):
    correlations = _service.correlate_fatigue_with_operations({aircraft_id: "default"})
    return {
        "aircraft_id": aircraft_id,
        "correlations": [
            {
                "mission_type": c.mission_type,
                "avg_consumption_rate": c.avg_consumption_rate,
                "avg_max_load_factor": c.avg_max_load_factor,
                "sample_count": c.sample_count,
                "correlation_coefficient": c.correlation_coefficient,
            }
            for c in correlations
        ],
    }