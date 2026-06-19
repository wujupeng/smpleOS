from fastapi import APIRouter, HTTPException

from src.domain.services.v1.fleet_twin_service import FleetTwinService
from src.domain.services.v1.twin_sync_service import TwinSyncService
from src.infrastructure.event_bus import event_bus

router = APIRouter()

_twin_sync_service = TwinSyncService(event_publisher=event_bus)
_fleet_twin_service = FleetTwinService(_twin_sync_service, event_publisher=event_bus)


@router.post("/twins/fleet/aggregate")
async def aggregate_fleet_data(body: dict):
    fleet_id = body.get("fleet_id", "")
    aircraft_list = body.get("aircraft_sn_list")
    fleet_twin = await _fleet_twin_service.aggregate_fleet_data(fleet_id, aircraft_list)
    return fleet_twin.to_dict()


@router.get("/twins/fleet/{fleet_id}/fault-statistics")
async def get_fleet_fault_statistics(fleet_id: str):
    fleet_twin = _fleet_twin_service.get_fleet_twin(fleet_id)
    if not fleet_twin:
        raise HTTPException(status_code=404, detail=f"Fleet twin not found for {fleet_id}")
    return fleet_twin.fault_statistics.to_dict()


@router.get("/twins/fleet/{fleet_id}/life-statistics")
async def get_fleet_life_statistics(fleet_id: str):
    fleet_twin = _fleet_twin_service.get_fleet_twin(fleet_id)
    if not fleet_twin:
        raise HTTPException(status_code=404, detail=f"Fleet twin not found for {fleet_id}")
    return fleet_twin.life_statistics.to_dict()


@router.get("/twins/fleet/{fleet_id}/maintenance-statistics")
async def get_fleet_maintenance_statistics(fleet_id: str):
    fleet_twin = _fleet_twin_service.get_fleet_twin(fleet_id)
    if not fleet_twin:
        raise HTTPException(status_code=404, detail=f"Fleet twin not found for {fleet_id}")
    return fleet_twin.maintenance_statistics.to_dict()


@router.get("/twins/fleet/{fleet_id}/anomalies")
async def detect_fleet_anomalies(fleet_id: str):
    result = await _fleet_twin_service.detect_fleet_anomaly(fleet_id)
    return result


@router.post("/twins/fleet/{fleet_id}/predictive-maintenance")
async def predictive_maintenance(fleet_id: str, body: dict):
    aircraft_sn = body.get("aircraft_sn", "")
    result = await _fleet_twin_service.predictive_maintenance(fleet_id, aircraft_sn)
    return result


@router.get("/twins/fleet/{fleet_id}/reliability")
async def fleet_reliability_analysis(fleet_id: str):
    result = await _fleet_twin_service.fleet_reliability_analysis(fleet_id)
    return result