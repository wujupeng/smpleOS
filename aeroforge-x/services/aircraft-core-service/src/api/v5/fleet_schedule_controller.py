from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.domain.services.fleet_intelligence.fleet_optimizer_service import FleetOptimizerService

router = APIRouter(prefix="/api/v5/aircraft-core/fleet", tags=["Fleet Schedule v5"])

_service = FleetOptimizerService()


@router.post("/schedules")
async def optimize_fleet_schedule(body: dict[str, Any]):
    aircraft_health = body.get("aircraft_health", {})
    mission_requirements = body.get("mission_requirements")
    schedule = _service.optimize_fleet_schedule(
        aircraft_health=aircraft_health,
        mission_requirements=mission_requirements,
    )
    return {
        "schedule_id": schedule.schedule_id,
        "aircraft_assignments": schedule.aircraft_assignments,
        "maintenance_windows": [
            {
                "window_id": w.window_id,
                "aircraft_id": w.aircraft_id,
                "start_time": w.start_time,
                "end_time": w.end_time,
                "maintenance_type": w.maintenance_type,
                "resource_availability": w.resource_availability,
                "operational_impact": w.operational_impact,
            }
            for w in schedule.maintenance_windows
        ],
        "total_operational_aircraft": schedule.total_operational_aircraft,
        "constraint_violations": schedule.constraint_violations,
        "optimization_score": schedule.optimization_score,
    }


@router.get("/aircraft/{aircraft_id}/maintenance-windows")
async def compute_maintenance_windows(aircraft_id: str):
    from fastapi import Query
    return {"message": "Use POST /fleet/schedules with aircraft_health data"}


@router.post("/what-if")
async def what_if_analysis(body: dict[str, Any]):
    from src.domain.services.fleet_intelligence.fleet_optimizer_service import FleetSchedule, MaintenanceWindow
    schedule_data = body.get("base_schedule", {})
    base_schedule = FleetSchedule(
        schedule_id=schedule_data.get("schedule_id", ""),
        aircraft_assignments=schedule_data.get("aircraft_assignments", {}),
        maintenance_windows=[],
        total_operational_aircraft=schedule_data.get("total_operational_aircraft", 0),
        constraint_violations=schedule_data.get("constraint_violations", []),
        optimization_score=schedule_data.get("optimization_score", 0.0),
    )
    scenario = body.get("scenario", {})
    result = _service.what_if_analysis(base_schedule=base_schedule, scenario=scenario)
    return result


@router.post("/resources/optimize")
async def optimize_fleet_resources(body: dict[str, Any]):
    aircraft_health = body.get("aircraft_health", {})
    resource_pool = body.get("resource_pool", {})
    result = _service.optimize_fleet_resources(
        aircraft_health=aircraft_health,
        resource_pool=resource_pool,
    )
    return result