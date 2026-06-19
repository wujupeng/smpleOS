from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.services.delivery_package_service import DeliveryPackageService
from ..domain.services.flight_test_plan_service import FlightTestPlanService
from ..domain.services.full_pipeline_service import FullPipelineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/delivery", tags=["Delivery Center"])

_flight_test_service = FlightTestPlanService()
_delivery_service = DeliveryPackageService()
_pipeline_service = FullPipelineService()


# --- Flight Test Plan APIs ---

class GenerateFlightTestPlanRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    aircraft_model: str = Field(..., min_length=1)
    certification_standard: str = Field(default="FAR-23", description="FAR-23|FAR-25|CCAR-23|CCAR-25")
    design_parameters: dict[str, Any] = {}


@router.post("/flight-test/generate", response_model=ApiResponse[dict])
async def generate_flight_test_plan(body: GenerateFlightTestPlanRequest):
    plan = _flight_test_service.generate_flight_test_plan(
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        aircraft_model=body.aircraft_model,
        certification_standard=body.certification_standard,
        design_parameters=body.design_parameters,
    )
    return ApiResponse(data=plan.to_dict())


@router.get("/flight-test/{plan_id}", response_model=ApiResponse[dict])
async def get_flight_test_plan(plan_id: str):
    plan = _flight_test_service.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Flight test plan not found")
    return ApiResponse(data=plan.to_dict())


@router.get("/flight-test/{plan_id}/coverage", response_model=ApiResponse[dict])
async def get_flight_test_coverage(plan_id: str):
    result = _flight_test_service.validate_coverage(plan_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return ApiResponse(data=result)


@router.get("/flight-test/{plan_id}/sequence", response_model=ApiResponse[dict])
async def get_optimized_sequence(plan_id: str):
    result = _flight_test_service.optimize_test_sequence(plan_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return ApiResponse(data=result)


@router.get("/flight-test/certification/{standard}", response_model=ApiResponse[dict])
async def map_certification_requirements(standard: str):
    result = _flight_test_service.map_certification_requirements(standard)
    return ApiResponse(data=result)


# --- Delivery Package APIs ---

class GenerateDeliveryPackageRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    aircraft_model: str = Field(..., min_length=1)
    available_documents: list[dict[str, Any]] = []
    package_type: str = Field(default="full", description="full|minimal")


@router.post("/package/generate", response_model=ApiResponse[dict])
async def generate_delivery_package(body: GenerateDeliveryPackageRequest):
    package = _delivery_service.generate_delivery_package(
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        aircraft_model=body.aircraft_model,
        available_documents=body.available_documents,
        package_type=body.package_type,
    )
    return ApiResponse(data=package.to_dict())


@router.get("/package/{package_id}", response_model=ApiResponse[dict])
async def get_delivery_package(package_id: str):
    package = _delivery_service.get_package(package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Delivery package not found")
    return ApiResponse(data=package.to_dict())


@router.get("/package/{package_id}/validate", response_model=ApiResponse[dict])
async def validate_package_completeness(package_id: str):
    result = _delivery_service.validate_completeness(package_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return ApiResponse(data=result)


@router.get("/package/{package_id}/index", response_model=ApiResponse[dict])
async def get_package_index(package_id: str):
    result = _delivery_service.generate_package_index(package_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return ApiResponse(data=result)


@router.get("/packages", response_model=ApiResponse[dict])
async def list_delivery_packages(tenant_id: str, project_id: str | None = None):
    packages = _delivery_service.list_packages(tenant_id, project_id)
    return ApiResponse(data={
        "total": len(packages),
        "packages": [p.to_dict() for p in packages],
    })


# --- Full Pipeline APIs ---

class GeneratePipelineRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    aircraft_spec: dict[str, Any] | None = None
    skip_stages: list[str] | None = None


@router.post("/pipeline/generate")
async def generate_full_pipeline(body: GeneratePipelineRequest):
    run = _pipeline_service.generate_full_delivery_package(
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        aircraft_spec=body.aircraft_spec,
        skip_stages=body.skip_stages,
    )
    return {"data": run.to_detail_dict()}


@router.get("/pipeline/{pipeline_id}/status")
async def get_pipeline_status(pipeline_id: str):
    run = _pipeline_service.get_pipeline_status(pipeline_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"data": run.get_progress()}


@router.get("/pipeline/{pipeline_id}/report")
async def get_pipeline_report(pipeline_id: str):
    report = _pipeline_service.get_pipeline_report(pipeline_id)
    if not report:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {"data": report}


@router.post("/pipeline/{pipeline_id}/retry")
async def retry_pipeline(pipeline_id: str):
    run = _pipeline_service.retry_failed_stage(pipeline_id)
    if not run:
        raise HTTPException(status_code=400, detail="Pipeline not found or not in failed state")
    return {"data": run.to_detail_dict()}


@router.get("/pipelines")
async def list_pipelines(tenant_id: str):
    runs = _pipeline_service.list_pipelines(tenant_id)
    return {"data": [r.to_dict() for r in runs]}