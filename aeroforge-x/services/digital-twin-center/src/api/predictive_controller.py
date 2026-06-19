from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.predictive_models import DegradationModelType
from ..domain.services.predictive_maintenance_service import PredictiveMaintenanceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/twins", tags=["Predictive Maintenance"])

_service = PredictiveMaintenanceService()


class BuildModelRequest(BaseModel):
    aircraft_sn: str = Field(..., min_length=1)
    component: str = Field(..., min_length=1)
    model_type: DegradationModelType = DegradationModelType.LINEAR
    training_data: list[dict[str, Any]] | None = None


class AnomalyDetectRequest(BaseModel):
    aircraft_sn: str = Field(..., min_length=1)
    component: str = Field(..., min_length=1)
    sensor_data: dict[str, float] = Field(default_factory=dict)


class OptimizeMaintenanceRequest(BaseModel):
    aircraft_sn: str = Field(..., min_length=1)
    components: list[str] | None = None


@router.post("/predictive/model", response_model=ApiResponse[dict])
async def build_model(body: BuildModelRequest):
    model = _service.build_degradation_model(
        aircraft_sn=body.aircraft_sn,
        component=body.component,
        model_type=body.model_type,
        training_data=body.training_data,
    )
    return ApiResponse(data=model.to_dict())


@router.get("/{aircraft_sn}/rul", response_model=ApiResponse[dict])
async def get_rul(aircraft_sn: str, component: str):
    prediction = _service.predict_remaining_useful_life(aircraft_sn, component)
    if prediction is None:
        raise HTTPException(status_code=404, detail="No degradation model found for this component")
    return ApiResponse(data=prediction.to_dict())


@router.get("/{aircraft_sn}/failure-probability", response_model=ApiResponse[dict])
async def get_failure_probability(aircraft_sn: str, component: str, threshold: float = 0.1):
    result = _service.predict_failure_probability(aircraft_sn, component, threshold)
    if result is None:
        raise HTTPException(status_code=404, detail="No degradation model found for this component")
    return ApiResponse(data=result.to_dict())


@router.post("/{aircraft_sn}/maintenance-optimization", response_model=ApiResponse[dict])
async def optimize_maintenance(aircraft_sn: str, body: OptimizeMaintenanceRequest):
    windows = _service.optimize_maintenance_schedule(aircraft_sn, body.components)
    return ApiResponse(data={
        "aircraft_sn": aircraft_sn,
        "total_windows": len(windows),
        "windows": [w.to_dict() for w in windows],
    })


@router.post("/predictive/anomaly", response_model=ApiResponse[dict])
async def detect_anomaly(body: AnomalyDetectRequest):
    detection = _service.detect_anomaly_advanced(
        aircraft_sn=body.aircraft_sn,
        component=body.component,
        sensor_data=body.sensor_data,
    )
    return ApiResponse(data=detection.to_dict())


@router.get("/{aircraft_sn}/anomalies", response_model=ApiResponse[dict])
async def get_anomalies(aircraft_sn: str):
    anomalies = _service.get_anomalies(aircraft_sn)
    return ApiResponse(data={
        "total": len(anomalies),
        "anomalies": [a.to_dict() for a in anomalies],
    })