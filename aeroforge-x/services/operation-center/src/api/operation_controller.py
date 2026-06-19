from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from src.domain.services.fleet_management_service import FleetManagementService
from src.domain.services.operation_analytics_service import OperationAnalyticsService
from src.domain.services.maintenance_scheduling_service import MaintenanceSchedulingService
from src.domain.services.flight_data_monitoring_service import FlightDataMonitoringService
from src.infrastructure.event_bus import event_bus

router = APIRouter()

_fleet_service = FleetManagementService(event_publisher=event_bus)
_analytics_service = OperationAnalyticsService(_fleet_service, event_publisher=event_bus)
_scheduling_service = MaintenanceSchedulingService(_fleet_service, event_publisher=event_bus)
_monitoring_service = FlightDataMonitoringService(_fleet_service, event_publisher=event_bus)


@router.post("/operations/fleet/register")
async def register_aircraft(body: dict):
    aircraft_sn = body.get("aircraft_sn", "")
    model = body.get("model", "")
    fleet_id = body.get("fleet_id")
    if not aircraft_sn or not model:
        raise HTTPException(status_code=400, detail="aircraft_sn and model are required")
    try:
        registration = await _fleet_service.register_aircraft(aircraft_sn, model, fleet_id)
        return registration.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/operations/fleet/status")
async def get_fleet_status(fleet_id: str | None = None):
    return _fleet_service.get_fleet_status(fleet_id)


@router.get("/operations/fleet/{aircraft_sn}/flight-hours")
async def get_flight_hours(aircraft_sn: str):
    aircraft = _fleet_service.get_aircraft(aircraft_sn)
    if not aircraft:
        raise HTTPException(status_code=404, detail=f"Aircraft {aircraft_sn} not found")
    return {
        "aircraft_sn": aircraft_sn,
        "total_flight_hours": aircraft.total_flight_hours,
        "status": aircraft.status.value,
    }


@router.post("/operations/maintenance/schedules")
async def create_maintenance_schedule(body: dict):
    aircraft_sn = body.get("aircraft_sn", "")
    maintenance_type = body.get("maintenance_type", "")
    scheduled_date_str = body.get("scheduled_date", "")
    estimated_duration = body.get("estimated_duration_hours", 8.0)
    if not aircraft_sn or not maintenance_type or not scheduled_date_str:
        raise HTTPException(status_code=400, detail="aircraft_sn, maintenance_type, and scheduled_date are required")
    try:
        scheduled_date = datetime.fromisoformat(scheduled_date_str).replace(tzinfo=timezone.utc)
        schedule = await _scheduling_service.create_maintenance_schedule(aircraft_sn, maintenance_type, scheduled_date, estimated_duration)
        return schedule.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/operations/analytics/utilization")
async def get_utilization_rate(fleet_id: str | None = None, period_days: int = 30):
    return _analytics_service.calculate_utilization_rate(fleet_id, period_days)


@router.get("/operations/analytics/dispatch-reliability")
async def get_dispatch_reliability(fleet_id: str | None = None, period_days: int = 30):
    return _analytics_service.calculate_dispatch_reliability(fleet_id, period_days)


@router.get("/operations/analytics/maintenance-cost")
async def get_maintenance_cost(fleet_id: str | None = None, period_days: int = 30):
    return _analytics_service.calculate_maintenance_cost(fleet_id, period_days)