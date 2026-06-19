from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.compliance import (
    CheckCategory,
    ComplianceStandard,
    ComplianceStatus,
)
from ..domain.services.compliance_domain_service import ComplianceDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance Management"])

_service = ComplianceDomainService()


class CheckDesignComplianceRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    aircraft_model: str = Field(..., min_length=1)
    standards: list[str] = Field(..., min_length=1)
    design_parameters: dict[str, Any] = {}


class CheckManufacturingComplianceRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    aircraft_model: str = Field(..., min_length=1)
    standards: list[str] = Field(..., min_length=1)
    manufacturing_data: dict[str, Any] = {}


class GenerateReportRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    aircraft_model: str = Field(..., min_length=1)
    standards: list[str] = Field(..., min_length=1)
    design_check_id: str | None = None
    manufacturing_check_id: str | None = None
    generated_by: str = ""


def _parse_standards(standards: list[str]) -> list[ComplianceStandard]:
    result = []
    for s in standards:
        try:
            result.append(ComplianceStandard(s))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid standard: {s}")
    return result


@router.post("/check/design", response_model=ApiResponse[dict])
async def check_design_compliance(body: CheckDesignComplianceRequest):
    standards = _parse_standards(body.standards)
    check = _service.check_design_compliance(
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        aircraft_model=body.aircraft_model,
        standards=standards,
        design_parameters=body.design_parameters,
    )
    return ApiResponse(data=check.to_dict())


@router.post("/check/manufacturing", response_model=ApiResponse[dict])
async def check_manufacturing_compliance(body: CheckManufacturingComplianceRequest):
    standards = _parse_standards(body.standards)
    check = _service.check_manufacturing_compliance(
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        aircraft_model=body.aircraft_model,
        standards=standards,
        manufacturing_data=body.manufacturing_data,
    )
    return ApiResponse(data=check.to_dict())


@router.post("/report", response_model=ApiResponse[dict])
async def generate_compliance_report(body: GenerateReportRequest):
    standards = _parse_standards(body.standards)
    report = _service.generate_compliance_report(
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        aircraft_model=body.aircraft_model,
        standards=standards,
        design_check_id=body.design_check_id,
        manufacturing_check_id=body.manufacturing_check_id,
        generated_by=body.generated_by,
    )
    return ApiResponse(data=report.to_dict())


@router.get("/checks/{check_id}", response_model=ApiResponse[dict])
async def get_compliance_check(check_id: str):
    check = _service.get_check(check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Compliance check not found")
    return ApiResponse(data=check.to_dict())


@router.get("/reports/{report_id}", response_model=ApiResponse[dict])
async def get_compliance_report(report_id: str):
    report = _service.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Compliance report not found")
    return ApiResponse(data=report.to_dict())


@router.get("/checks", response_model=ApiResponse[dict])
async def list_compliance_checks(tenant_id: str, project_id: str | None = None):
    checks = _service.list_checks(tenant_id, project_id)
    return ApiResponse(data={
        "total": len(checks),
        "checks": [c.to_dict() for c in checks],
    })


@router.get("/reports", response_model=ApiResponse[dict])
async def list_compliance_reports(tenant_id: str, project_id: str | None = None):
    reports = _service.list_reports(tenant_id, project_id)
    return ApiResponse(data={
        "total": len(reports),
        "reports": [r.to_dict() for r in reports],
    })


@router.get("/requirements/{standard}", response_model=ApiResponse[dict])
async def get_requirements(standard: str):
    try:
        std = ComplianceStandard(standard)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid standard: {standard}")
    requirements = _service.get_requirements(std)
    return ApiResponse(data={
        "standard": standard,
        "total": len(requirements),
        "requirements": [r.to_dict() for r in requirements],
    })