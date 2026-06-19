from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.unified_twin import ConflictResolution, InsightSeverity
from ..domain.services.twin_fusion_domain_service import TwinFusionDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/twins/unified", tags=["Unified Twin Fusion"])

_service = TwinFusionDomainService()


class CreateUnifiedTwinRequest(BaseModel):
    aircraft_serial_number: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    design_twin_id: str | None = None
    manufacturing_twin_id: str | None = None
    flight_twin_id: str | None = None
    maintenance_twin_id: str | None = None


class FuseTwinDataRequest(BaseModel):
    design_data: dict[str, Any] | None = None
    manufacturing_data: dict[str, Any] | None = None
    flight_data: dict[str, Any] | None = None
    maintenance_data: dict[str, Any] | None = None


class ReconcileConflictRequest(BaseModel):
    resolution: str = Field(..., description="measured_wins|design_wins|inferred_wins|manual_review")
    resolved_by: str = ""


@router.post("", response_model=ApiResponse[dict])
async def create_unified_twin(body: CreateUnifiedTwinRequest):
    twin = _service.create_unified_twin(
        aircraft_serial_number=body.aircraft_serial_number,
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        design_twin_id=body.design_twin_id,
        manufacturing_twin_id=body.manufacturing_twin_id,
        flight_twin_id=body.flight_twin_id,
        maintenance_twin_id=body.maintenance_twin_id,
    )
    return ApiResponse(data=twin.to_dict())


@router.get("/{aircraft_sn}", response_model=ApiResponse[dict])
async def get_unified_twin(aircraft_sn: str):
    twin = _service.get_unified_twin(aircraft_sn)
    if twin is None:
        raise HTTPException(status_code=404, detail="Unified twin not found")
    return ApiResponse(data=twin.to_detail_dict())


@router.post("/{aircraft_sn}/fuse", response_model=ApiResponse[dict])
async def fuse_twin_data(aircraft_sn: str, body: FuseTwinDataRequest):
    result = _service.fuse_twin_data(
        aircraft_sn=aircraft_sn,
        design_data=body.design_data,
        manufacturing_data=body.manufacturing_data,
        flight_data=body.flight_data,
        maintenance_data=body.maintenance_data,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return ApiResponse(data=result)


@router.get("/{aircraft_sn}/insights", response_model=ApiResponse[dict])
async def get_cross_twin_insights(aircraft_sn: str, severity: str | None = None):
    parsed_severity = None
    if severity:
        try:
            parsed_severity = InsightSeverity(severity)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    insights = _service.get_insights(aircraft_sn, parsed_severity)
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "insights": insights, "total": len(insights)})


@router.get("/{aircraft_sn}/anomalies", response_model=ApiResponse[dict])
async def detect_cross_twin_anomalies(aircraft_sn: str):
    anomalies = _service.detect_cross_twin_anomaly(aircraft_sn)
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "anomalies": anomalies, "total": len(anomalies)})


@router.post("/{aircraft_sn}/conflicts/{conflict_id}/reconcile", response_model=ApiResponse[dict])
async def reconcile_conflict(aircraft_sn: str, conflict_id: str, body: ReconcileConflictRequest):
    try:
        resolution = ConflictResolution(body.resolution)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid resolution: {body.resolution}")
    result = _service.reconcile_conflicts(aircraft_sn, conflict_id, resolution, body.resolved_by)
    if not result.get("resolved"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Reconciliation failed"))
    return ApiResponse(data=result)


@router.post("/{aircraft_sn}/insights/{insight_id}/propagate", response_model=ApiResponse[dict])
async def propagate_insight(aircraft_sn: str, insight_id: str):
    result = _service.propagate_insight(aircraft_sn, insight_id)
    if not result.get("propagated"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Propagation failed"))
    return ApiResponse(data=result)