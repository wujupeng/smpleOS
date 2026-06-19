from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.spc_control_chart import ChartType, SpecificationLimits
from ..domain.services.spc_domain_service import SPCDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/qms/spc", tags=["SPC"])

_service = SPCDomainService()


class SpecLimitsRequest(BaseModel):
    usl: float
    lsl: float
    target: float


class CreateChartRequest(BaseModel):
    tenant_id: str = Field(default="default")
    project_id: str = Field(default="default")
    chart_type: ChartType = ChartType.X_BAR_R
    process_name: str = Field(..., min_length=1)
    characteristic_name: str = Field(..., min_length=1)
    specification_limits: SpecLimitsRequest
    sample_size: int = Field(default=5, ge=2, le=25)
    sampling_frequency: str = "per_lot"
    created_by: str = ""


class AddMeasurementRequest(BaseModel):
    sample_group: int = Field(..., ge=1)
    measurement_values: list[float] = Field(..., min_length=1)
    measured_by: str = ""


@router.post("/charts", response_model=ApiResponse[dict])
async def create_chart(body: CreateChartRequest):
    spec_limits = SpecificationLimits(
        usl=body.specification_limits.usl,
        lsl=body.specification_limits.lsl,
        target=body.specification_limits.target,
    )
    chart = _service.create_control_chart(
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        chart_type=body.chart_type,
        process_name=body.process_name,
        characteristic_name=body.characteristic_name,
        specification_limits=spec_limits,
        sample_size=body.sample_size,
        sampling_frequency=body.sampling_frequency,
        created_by=body.created_by,
    )
    return ApiResponse(data=chart.to_dict())


@router.get("/charts", response_model=ApiResponse[dict])
async def list_charts(
    tenant_id: str | None = None,
    project_id: str | None = None,
):
    charts = _service.list_charts(tenant_id, project_id)
    return ApiResponse(data={
        "total": len(charts),
        "charts": [c.to_dict() for c in charts],
    })


@router.get("/charts/{chart_id}", response_model=ApiResponse[dict])
async def get_chart(chart_id: str):
    chart = _service.get_chart(chart_id)
    if chart is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    measurements = _service.get_measurements(chart_id)
    return ApiResponse(data={
        **chart.to_dict(),
        "measurements": [m.to_dict() for m in measurements],
    })


@router.post("/charts/{chart_id}/measurements", response_model=ApiResponse[dict])
async def add_measurement(chart_id: str, body: AddMeasurementRequest):
    measurement = _service.add_measurement(
        chart_id=chart_id,
        sample_group=body.sample_group,
        measurement_values=body.measurement_values,
        measured_by=body.measured_by,
    )
    if measurement is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    return ApiResponse(data=measurement.to_dict())


@router.post("/charts/{chart_id}/calculate-limits", response_model=ApiResponse[dict])
async def calculate_limits(chart_id: str):
    chart = _service.calculate_control_limits(chart_id)
    if chart is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    return ApiResponse(data=chart.to_dict())


@router.get("/charts/{chart_id}/capability", response_model=ApiResponse[dict])
async def get_capability(chart_id: str):
    capability = _service.calculate_process_capability(chart_id)
    if capability is None:
        raise HTTPException(status_code=404, detail="Chart not found or insufficient data")
    return ApiResponse(data=capability.to_dict())


@router.get("/charts/{chart_id}/report", response_model=ApiResponse[dict])
async def get_report(chart_id: str):
    report = _service.generate_spc_report(chart_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    return ApiResponse(data=report)