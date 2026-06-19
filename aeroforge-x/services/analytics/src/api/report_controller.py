from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.report import ReportFormat, ReportStatus, ReportTemplate
from ..domain.services.report_domain_service import ReportDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics/reports", tags=["Reports"])

_service = ReportDomainService()


class CreateReportRequest(BaseModel):
    tenant_id: str = Field(default="default")
    name: str = Field(..., min_length=1)
    report_type: str = Field(..., min_length=1)
    template_id: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    format: ReportFormat = ReportFormat.PDF
    generated_by: str = ""


class ScheduleReportRequest(BaseModel):
    cron_expression: str = Field(..., min_length=1)


@router.post("", response_model=ApiResponse[dict])
async def create_report(body: CreateReportRequest):
    report = _service.create_report(
        tenant_id=body.tenant_id,
        name=body.name,
        report_type=body.report_type,
        template_id=body.template_id,
        parameters=body.parameters,
        format=body.format,
        generated_by=body.generated_by,
    )
    return ApiResponse(data=report.to_dict())


@router.get("", response_model=ApiResponse[dict])
async def list_reports(
    tenant_id: str | None = None,
    report_type: str | None = None,
    status: ReportStatus | None = None,
):
    reports = _service.list_reports(tenant_id, report_type, status)
    return ApiResponse(data={
        "total": len(reports),
        "reports": [r.to_dict() for r in reports],
    })


@router.get("/templates", response_model=ApiResponse[dict])
async def get_templates():
    templates = _service.get_templates()
    return ApiResponse(data={
        "templates": {k: v for k, v in templates.items()},
    })


@router.get("/{report_id}", response_model=ApiResponse[dict])
async def get_report(report_id: str):
    report = _service.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return ApiResponse(data=report.to_dict())


@router.post("/{report_id}/generate", response_model=ApiResponse[dict])
async def generate_report(report_id: str):
    report = _service.generate_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return ApiResponse(data=report.to_dict())


@router.post("/{report_id}/schedule", response_model=ApiResponse[dict])
async def schedule_report(report_id: str, body: ScheduleReportRequest):
    report = _service.schedule_report(report_id, body.cron_expression)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return ApiResponse(data=report.to_dict())


@router.post("/{report_id}/share", response_model=ApiResponse[dict])
async def share_report(report_id: str):
    report = _service.share_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return ApiResponse(data=report.to_dict())