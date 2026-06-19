from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.digital_twin import DigitalTwin, SyncStatus, TwinType
from ..domain.services.twin_domain_service import TwinDomainService
from ..domain.services.design_twin_service import DesignTwinService
from ..domain.services.manufacturing_twin_service import ManufacturingTwinService
from ..domain.services.twin_loop_service import (
    ConflictResolution,
    FeedbackType,
    TwinLoopService,
)
from ..domain.services.flight_twin_service import FlightTwinService
from ..domain.services.maintenance_twin_service import MaintenanceTwinService, MaintenanceType, MaintenanceContent, MaintenanceResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/twin", tags=["Digital Twin"])

_twin_service = TwinDomainService()
_design_twin_service = DesignTwinService(_twin_service)
_manufacturing_twin_service = ManufacturingTwinService(_twin_service)
_loop_service = TwinLoopService(_twin_service, _design_twin_service, _manufacturing_twin_service)
_flight_twin_service = FlightTwinService(_twin_service)
_maintenance_twin_service = MaintenanceTwinService(_twin_service)


class CreateTwinRequest(BaseModel):
    aircraft_serial_number: str
    twin_type: str = "design"
    entity_id: str = ""
    entity_type: str = ""


class SyncTwinRequest(BaseModel):
    sync_type: str
    payload: dict[str, Any] | None = None


class SyncDesignRequest(BaseModel):
    aircraft_serial_number: str
    design_params: dict[str, Any]
    changed_by: str = "system"
    reason: str = "design_update"


class SyncManufacturingRequest(BaseModel):
    aircraft_serial_number: str
    measurement_data: dict[str, float]
    design_data: dict[str, float] | None = None
    tolerances: dict[str, float] | None = None


class FeedbackToDesignRequest(BaseModel):
    aircraft_serial_number: str
    source_type: str = "manufacturing"
    override_params: dict[str, Any] | None = None


class FeedbackToMaintenanceRequest(BaseModel):
    aircraft_serial_number: str
    design_changes: dict[str, Any] | None = None


class DetectConflictRequest(BaseModel):
    aircraft_serial_number: str
    manufacturing_data: dict[str, float] | None = None
    flight_data: dict[str, float] | None = None
    conflict_threshold: float = Field(default=0.05, gt=0, le=1.0)


class ResolveFeedbackRequest(BaseModel):
    action: str = "approved"


class ResolveConflictRequest(BaseModel):
    resolution: str = "manufacturing_wins"
    resolved_value: float | None = None


@router.post("/create", response_model=ApiResponse[dict])
async def create_twin(body: CreateTwinRequest):
    twin = _twin_service.create_twin(
        aircraft_serial_number=body.aircraft_serial_number,
        twin_type=TwinType(body.twin_type),
        entity_id=body.entity_id,
        entity_type=body.entity_type,
    )
    return ApiResponse(data=twin.to_dict())


@router.get("/list", response_model=ApiResponse[dict])
async def list_twins(twin_type: str | None = None):
    tt = TwinType(twin_type) if twin_type else None
    twins = _twin_service.list_twins(tt)
    return ApiResponse(data={
        "total": len(twins),
        "twins": [t.to_dict() for t in twins],
    })


@router.get("/{twin_id}", response_model=ApiResponse[dict])
async def get_twin(twin_id: str):
    twin = _twin_service.get_twin(twin_id)
    if twin is None:
        raise HTTPException(status_code=404, detail="Twin not found")
    return ApiResponse(data=twin.to_dict())


@router.post("/{twin_id}/sync", response_model=ApiResponse[dict])
async def sync_twin(twin_id: str, body: SyncTwinRequest):
    twin = _twin_service.sync_twin(twin_id, body.sync_type, body.payload)
    if twin is None:
        raise HTTPException(status_code=404, detail="Twin not found")
    return ApiResponse(data=twin.to_dict())


@router.get("/{twin_id}/sync-status", response_model=ApiResponse[dict])
async def check_sync_status(twin_id: str):
    result = _twin_service.check_sync_status(twin_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Twin not found")
    return ApiResponse(data=result)


@router.get("/{twin_id}/safety-restrictions", response_model=ApiResponse[dict])
async def check_safety_restrictions(twin_id: str):
    result = _twin_service.restrict_safety_decisions(twin_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Twin not found")
    return ApiResponse(data=result)


@router.get("/aircraft/{aircraft_sn}/overview", response_model=ApiResponse[dict])
async def get_aircraft_twin_overview(aircraft_sn: str):
    twins = _twin_service.get_twin_by_aircraft_sn(aircraft_sn)
    overview: dict[str, Any] = {
        "aircraft_sn": aircraft_sn,
        "twin_count": len(twins),
        "twins": {},
    }
    for twin in twins:
        twin_info = {
            "twin_id": twin.id,
            "sync_status": twin.sync_status.value,
            "data_version": twin.data_version,
            "last_sync_time": twin.last_sync_time.isoformat() if twin.last_sync_time else None,
        }
        overview["twins"][twin.twin_type.value] = twin_info
    return ApiResponse(data=overview)


@router.post("/design/sync", response_model=ApiResponse[dict])
async def sync_design_twin(body: SyncDesignRequest):
    twin = _design_twin_service.sync_with_design(
        aircraft_sn=body.aircraft_serial_number,
        design_params=body.design_params,
        changed_by=body.changed_by,
        reason=body.reason,
    )
    if twin is None:
        raise HTTPException(status_code=500, detail="Failed to sync design twin")
    return ApiResponse(data=twin.to_dict())


@router.get("/design/{aircraft_sn}/snapshot", response_model=ApiResponse[dict])
async def get_design_snapshot(aircraft_sn: str, as_of: str | None = None):
    result = _design_twin_service.get_design_snapshot(aircraft_sn, as_of)
    if result is None:
        raise HTTPException(status_code=404, detail="Design twin not found")
    return ApiResponse(data=result)


@router.get("/design/{aircraft_sn}/param-history", response_model=ApiResponse[dict])
async def get_design_param_history(aircraft_sn: str):
    history = _design_twin_service.get_param_history(aircraft_sn)
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "param_history": history})


@router.post("/manufacturing/sync", response_model=ApiResponse[dict])
async def sync_manufacturing_twin(body: SyncManufacturingRequest):
    twin = _manufacturing_twin_service.sync_with_measurement(
        aircraft_sn=body.aircraft_serial_number,
        measurement_data=body.measurement_data,
        design_data=body.design_data,
        tolerances=body.tolerances,
    )
    if twin is None:
        raise HTTPException(status_code=500, detail="Failed to sync manufacturing twin")
    return ApiResponse(data=twin.to_dict())


@router.get("/manufacturing/{aircraft_sn}/snapshot", response_model=ApiResponse[dict])
async def get_manufacturing_snapshot(aircraft_sn: str):
    result = _manufacturing_twin_service.get_manufacturing_snapshot(aircraft_sn)
    if result is None:
        raise HTTPException(status_code=404, detail="Manufacturing twin not found")
    return ApiResponse(data=result)


@router.get("/manufacturing/{aircraft_sn}/deviation-stats", response_model=ApiResponse[dict])
async def get_deviation_statistics(aircraft_sn: str):
    result = _manufacturing_twin_service.get_deviation_statistics(aircraft_sn)
    return ApiResponse(data=result)


@router.get("/manufacturing/{aircraft_sn}/compare-design", response_model=ApiResponse[dict])
async def compare_manufacturing_with_design(aircraft_sn: str):
    result = _manufacturing_twin_service.compare_with_design(aircraft_sn)
    if result is None:
        raise HTTPException(status_code=404, detail="Manufacturing twin not found")
    return ApiResponse(data=result)


@router.post("/loop/feedback-to-design", response_model=ApiResponse[dict])
async def feedback_to_design(body: FeedbackToDesignRequest):
    record = _loop_service.feedback_to_design(
        aircraft_sn=body.aircraft_serial_number,
        source_type=body.source_type,
        override_params=body.override_params,
    )
    if record is None:
        return ApiResponse(data={"message": "No feedback generated - conditions not met"})
    return ApiResponse(data=record.to_dict())


@router.post("/loop/feedback-to-maintenance", response_model=ApiResponse[dict])
async def feedback_to_maintenance(body: FeedbackToMaintenanceRequest):
    record = _loop_service.feedback_to_maintenance(
        aircraft_sn=body.aircraft_serial_number,
        design_changes=body.design_changes,
    )
    if record is None:
        return ApiResponse(data={"message": "No feedback generated - no maintenance-impacting changes"})
    return ApiResponse(data=record.to_dict())


@router.post("/loop/detect-conflict", response_model=ApiResponse[dict])
async def detect_conflict(body: DetectConflictRequest):
    conflicts = _loop_service.detect_conflict(
        aircraft_sn=body.aircraft_serial_number,
        manufacturing_data=body.manufacturing_data,
        flight_data=body.flight_data,
        conflict_threshold=body.conflict_threshold,
    )
    return ApiResponse(data={
        "aircraft_sn": body.aircraft_serial_number,
        "conflict_count": len(conflicts),
        "conflicts": [c.to_dict() for c in conflicts],
        "resolution_policy": "manufacturing_measured_data_takes_precedence",
    })


@router.get("/loop/feedback-records", response_model=ApiResponse[dict])
async def get_feedback_records(aircraft_sn: str | None = None, feedback_type: str | None = None):
    ft = FeedbackType(feedback_type) if feedback_type else None
    records = _loop_service.get_feedback_records(aircraft_sn, ft)
    return ApiResponse(data={
        "total": len(records),
        "records": [r.to_dict() for r in records],
    })


@router.get("/loop/conflict-records", response_model=ApiResponse[dict])
async def get_conflict_records(aircraft_sn: str | None = None):
    records = _loop_service.get_conflict_records(aircraft_sn)
    return ApiResponse(data={
        "total": len(records),
        "records": [c.to_dict() for c in records],
    })


@router.put("/loop/feedback/{feedback_id}/resolve", response_model=ApiResponse[dict])
async def resolve_feedback(feedback_id: str, body: ResolveFeedbackRequest):
    record = _loop_service.resolve_feedback(feedback_id, body.action)
    if record is None:
        raise HTTPException(status_code=404, detail="Feedback record not found")
    return ApiResponse(data=record.to_dict())


@router.put("/loop/conflict/{conflict_id}/resolve", response_model=ApiResponse[dict])
async def resolve_conflict(conflict_id: str, body: ResolveConflictRequest):
    resolution = ConflictResolution(body.resolution)
    record = _loop_service.resolve_conflict(conflict_id, resolution, body.resolved_value)
    if record is None:
        raise HTTPException(status_code=404, detail="Conflict record not found")
    return ApiResponse(data=record.to_dict())


class IngestTelemetryRequest(BaseModel):
    aircraft_serial_number: str
    telemetry_data: list[dict[str, Any]]


class AssessHealthRequest(BaseModel):
    aircraft_serial_number: str
    component_loads: dict[str, float] | None = None
    flight_hours: float = 0.0


class DetectAnomalyRequest(BaseModel):
    aircraft_serial_number: str
    sensor_data: dict[str, float]


@router.post("/flight/ingest", response_model=ApiResponse[dict])
async def ingest_telemetry(body: IngestTelemetryRequest):
    twin = _flight_twin_service.ingest_telemetry(body.aircraft_serial_number, body.telemetry_data)
    if twin is None:
        return ApiResponse(data={"message": "Telemetry ingestion failed"})
    return ApiResponse(data=twin.to_dict())


@router.get("/flight/{aircraft_sn}/health", response_model=ApiResponse[dict])
async def get_health_assessment(aircraft_sn: str):
    assessments = _flight_twin_service.get_health_assessment(aircraft_sn)
    return ApiResponse(data={
        "aircraft_sn": aircraft_sn,
        "assessment_count": len(assessments),
        "assessments": assessments,
    })


@router.post("/flight/assess-health", response_model=ApiResponse[dict])
async def assess_structural_health(body: AssessHealthRequest):
    assessments = _flight_twin_service.assess_structural_health(
        aircraft_sn=body.aircraft_serial_number,
        component_loads=body.component_loads,
        flight_hours=body.flight_hours,
    )
    return ApiResponse(data={
        "aircraft_sn": body.aircraft_serial_number,
        "assessment_count": len(assessments),
        "assessments": [a.to_dict() for a in assessments],
    })


@router.post("/flight/detect-anomaly", response_model=ApiResponse[dict])
async def detect_anomaly(body: DetectAnomalyRequest):
    anomalies = _flight_twin_service.detect_anomaly(
        aircraft_sn=body.aircraft_serial_number,
        sensor_data=body.sensor_data,
    )
    return ApiResponse(data={
        "aircraft_sn": body.aircraft_serial_number,
        "anomaly_count": len(anomalies),
        "anomalies": [a.to_dict() for a in anomalies],
    })


@router.get("/flight/{aircraft_sn}/load-trend", response_model=ApiResponse[dict])
async def analyze_load_trend(aircraft_sn: str, metric_name: str = "wing_lift"):
    result = _flight_twin_service.analyze_load_trend(aircraft_sn, metric_name)
    return ApiResponse(data=result)


class RecordMaintenanceRequest(BaseModel):
    aircraft_serial_number: str
    maintenance_type: str = "preventive"
    content: str = "inspection"
    result: str = "completed"
    component_id: str = ""
    component_name: str = ""
    description: str = ""
    performed_by: str = ""
    flight_hours: float = 0.0
    parts_replaced: list[str] | None = None


class EstimateLifeRequest(BaseModel):
    aircraft_serial_number: str
    flight_hours: float = 0.0
    health_assessments: list[dict[str, Any]] | None = None


class GeneratePlanRequest(BaseModel):
    aircraft_serial_number: str
    flight_hours: float = 0.0
    health_assessments: list[dict[str, Any]] | None = None
    anomalies: list[dict[str, Any]] | None = None


@router.post("/maintenance/record", response_model=ApiResponse[dict])
async def record_maintenance(body: RecordMaintenanceRequest):
    record = _maintenance_twin_service.record_maintenance(
        aircraft_sn=body.aircraft_serial_number,
        maintenance_type=MaintenanceType(body.maintenance_type),
        content=MaintenanceContent(body.content),
        result=MaintenanceResult(body.result),
        component_id=body.component_id,
        component_name=body.component_name,
        description=body.description,
        performed_by=body.performed_by,
        flight_hours=body.flight_hours,
        parts_replaced=body.parts_replaced,
    )
    return ApiResponse(data=record.to_dict())


@router.get("/maintenance/{aircraft_sn}/records", response_model=ApiResponse[dict])
async def get_maintenance_records(aircraft_sn: str):
    records = _maintenance_twin_service.get_maintenance_records(aircraft_sn)
    return ApiResponse(data={
        "aircraft_sn": aircraft_sn,
        "total": len(records),
        "records": records,
    })


@router.post("/maintenance/estimate-life", response_model=ApiResponse[dict])
async def estimate_remaining_life(body: EstimateLifeRequest):
    estimates = _maintenance_twin_service.estimate_remaining_life(
        aircraft_sn=body.aircraft_serial_number,
        flight_hours=body.flight_hours,
        health_assessments=body.health_assessments,
    )
    return ApiResponse(data={
        "aircraft_sn": body.aircraft_serial_number,
        "estimates": [e.to_dict() for e in estimates],
    })


@router.post("/maintenance/generate-plan", response_model=ApiResponse[dict])
async def generate_maintenance_plan(body: GeneratePlanRequest):
    plan = _maintenance_twin_service.generate_maintenance_plan(
        aircraft_sn=body.aircraft_serial_number,
        flight_hours=body.flight_hours,
        health_assessments=body.health_assessments,
        anomalies=body.anomalies,
    )
    return ApiResponse(data={
        "aircraft_sn": body.aircraft_serial_number,
        "plan_items": [p.to_dict() for p in plan],
    })