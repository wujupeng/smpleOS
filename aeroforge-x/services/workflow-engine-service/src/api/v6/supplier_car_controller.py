from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.supplier.supplier_car_service import (
    SupplierCARService,
    SupplierQualityIssue,
    IssueSeverity,
)

router = APIRouter(prefix="/api/v6/workflow-engine", tags=["Supplier CAR v6"])

_car_service = SupplierCARService()


@router.post("/supplier-quality-issues")
async def create_quality_issue(body: dict[str, Any]):
    issue = SupplierQualityIssue(
        issue_id=body.get("issue_id", ""),
        supplier_id=body.get("supplier_id", ""),
        issue_type=body.get("issue_type", ""),
        description=body.get("description", ""),
        severity=IssueSeverity(body.get("severity", "Major")),
        correlated_lots=body.get("correlated_lots", []),
        correlated_ndt_records=body.get("correlated_ndt_records", []),
        affected_aircraft=body.get("affected_aircraft", []),
    )
    try:
        result = _car_service.createQualityIssue(issue=issue)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/supplier-quality-issues/{issue_id}/car")
async def create_car(issue_id: str):
    try:
        car = _car_service.createCAR(issue_id=issue_id)
        return car.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/cars/{car_id}/timeliness")
async def track_car_timeliness(car_id: str):
    try:
        result = _car_service.trackCARTimeliness(car_id=car_id)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cars/{car_id}/verify")
async def verify_corrective_action(car_id: str, body: dict[str, Any]):
    is_effective = body.get("is_effective", True)
    try:
        result = _car_service.verifyCorrectiveAction(car_id=car_id, is_effective=is_effective)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/supplier-quality-dashboards")
async def generate_quality_dashboard():
    dashboard = _car_service.generateQualityDashboard()
    return dashboard.to_dict()