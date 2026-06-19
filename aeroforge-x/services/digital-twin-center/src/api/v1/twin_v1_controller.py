from fastapi import APIRouter, HTTPException

from src.domain.services.v1.twin_sync_service import TwinSyncService
from src.domain.services.v1.twin_feedback_service import TwinFeedbackService
from src.infrastructure.event_bus import event_bus

router = APIRouter()

_twin_sync_service = TwinSyncService(event_publisher=event_bus)
_twin_feedback_service = TwinFeedbackService(_twin_sync_service, event_publisher=event_bus)


@router.get("/twins/design/{aircraft_sn}")
async def get_design_twin(aircraft_sn: str):
    twin = _twin_sync_service.get_design_twin(aircraft_sn)
    if not twin:
        raise HTTPException(status_code=404, detail=f"Design twin not found for {aircraft_sn}")
    return twin.to_dict()


@router.post("/twins/design/{aircraft_sn}/sync")
async def sync_design_twin(aircraft_sn: str, body: dict):
    parameters = body.get("parameters", [])
    model_version = body.get("model_version", 1)
    twin = await _twin_sync_service.sync_design_twin(aircraft_sn, parameters, model_version)
    return twin.to_dict()


@router.get("/twins/manufacturing/{aircraft_sn}")
async def get_manufacturing_twin(aircraft_sn: str):
    twin = _twin_sync_service.get_manufacturing_twin(aircraft_sn)
    if not twin:
        raise HTTPException(status_code=404, detail=f"Manufacturing twin not found for {aircraft_sn}")
    return twin.to_dict()


@router.post("/twins/manufacturing/{aircraft_sn}/sync")
async def sync_manufacturing_twin(aircraft_sn: str, body: dict):
    dimensions = body.get("dimensions", {})
    deviations = body.get("deviations", [])
    process_records = body.get("process_records", [])
    twin = await _twin_sync_service.sync_manufacturing_twin(aircraft_sn, dimensions, deviations, process_records)
    return twin.to_dict()


@router.get("/twins/flight/{aircraft_sn}")
async def get_flight_twin(aircraft_sn: str):
    twin = _twin_sync_service.get_flight_twin(aircraft_sn)
    if not twin:
        raise HTTPException(status_code=404, detail=f"Flight twin not found for {aircraft_sn}")
    return twin.to_dict()


@router.post("/twins/flight/{aircraft_sn}/sync")
async def sync_flight_twin(aircraft_sn: str, body: dict):
    flight_params = body.get("flight_parameters", {})
    loads = body.get("structural_loads")
    systems = body.get("system_status")
    twin = await _twin_sync_service.sync_flight_twin(aircraft_sn, flight_params, loads, systems)
    return twin.to_dict()


@router.get("/twins/maintenance/{aircraft_sn}")
async def get_maintenance_twin(aircraft_sn: str):
    twin = _twin_sync_service.get_maintenance_twin(aircraft_sn)
    if not twin:
        raise HTTPException(status_code=404, detail=f"Maintenance twin not found for {aircraft_sn}")
    return twin.to_dict()


@router.post("/twins/maintenance/{aircraft_sn}/sync")
async def sync_maintenance_twin(aircraft_sn: str, body: dict):
    records = body.get("records", [])
    replacements = body.get("replacements", [])
    life_updates = body.get("life_updates", [])
    twin = await _twin_sync_service.sync_maintenance_twin(aircraft_sn, records, replacements, life_updates)
    return twin.to_dict()


@router.get("/twins/{aircraft_sn}/feedback/flight-to-design")
async def feedback_flight_to_design(aircraft_sn: str):
    result = await _twin_feedback_service.feedback_flight_to_design(aircraft_sn)
    return result


@router.get("/twins/{aircraft_sn}/feedback/mfg-to-design")
async def feedback_mfg_to_design(aircraft_sn: str):
    result = await _twin_feedback_service.feedback_manufacturing_to_design(aircraft_sn)
    return result


@router.get("/twins/{aircraft_sn}/feedback/flight-to-maintenance")
async def feedback_flight_to_maintenance(aircraft_sn: str):
    result = await _twin_feedback_service.feedback_flight_to_maintenance(aircraft_sn)
    return result


@router.get("/twins/{aircraft_sn}/feedback/maintenance-to-mfg")
async def feedback_maintenance_to_mfg(aircraft_sn: str):
    result = await _twin_feedback_service.feedback_maintenance_to_manufacturing(aircraft_sn)
    return result