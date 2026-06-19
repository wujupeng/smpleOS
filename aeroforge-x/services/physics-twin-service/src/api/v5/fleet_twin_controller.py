from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.fleet_intelligence.fleet_twin_aggregator_service import (
    FleetTwinAggregatorService,
    FleetFilter,
    HealthStatus,
)

router = APIRouter(prefix="/api/v5/physics-twin/fleet", tags=["Fleet Twin Aggregator v5"])

_service = FleetTwinAggregatorService()


@router.post("/aircraft")
async def register_aircraft(body: dict[str, Any]):
    entry = _service.register_aircraft(
        tail_number=body.get("tail_number", ""),
        aircraft_type=body.get("aircraft_type", ""),
        operator=body.get("operator", ""),
        region=body.get("region", ""),
        age_years=body.get("age_years", 0.0),
        mission_profile=body.get("mission_profile", ""),
        twin_instance_id=body.get("twin_instance_id", ""),
    )
    return entry.to_dict()


@router.post("/health-indicator")
async def compute_fleet_health_indicator(body: dict[str, Any]):
    fleet_filter = None
    if body.get("filter"):
        f = body["filter"]
        fleet_filter = FleetFilter(
            aircraft_type=f.get("aircraft_type"),
            operator=f.get("operator"),
            region=f.get("region"),
            age_range=tuple(f["age_range"]) if f.get("age_range") else None,
            mission_profile=f.get("mission_profile"),
            health_status=HealthStatus(f["health_status"]) if f.get("health_status") else None,
        )

    result = _service.compute_fleet_health_indicator(fleet_filter=fleet_filter)
    return {
        "indicator_id": result.indicator_id,
        "filter_hash": result.filter_hash,
        "total_aircraft": result.total_aircraft,
        "healthy_count": result.healthy_count,
        "warning_count": result.warning_count,
        "critical_count": result.critical_count,
        "average_rul_hours": result.average_rul_hours,
        "average_fatigue_consumption": result.average_fatigue_consumption,
        "confidence_interval": result.confidence_interval,
        "is_sampled": result.is_sampled,
        "sample_size": result.sample_size,
    }


@router.get("/dashboard")
async def get_fleet_dashboard():
    dashboard = _service.get_fleet_status_dashboard()
    return {
        "total_aircraft": dashboard.total_aircraft,
        "health_summary": dashboard.health_summary,
        "region_breakdown": dashboard.region_breakdown,
        "operator_breakdown": dashboard.operator_breakdown,
        "type_breakdown": dashboard.type_breakdown,
        "average_age": dashboard.average_age,
        "average_rul_hours": dashboard.average_rul_hours,
    }


@router.get("/aircraft/{aircraft_id}/detail")
async def drill_down_aircraft(aircraft_id: str):
    entry = _service.drill_down_aircraft(aircraft_id=aircraft_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    return entry.to_dict()