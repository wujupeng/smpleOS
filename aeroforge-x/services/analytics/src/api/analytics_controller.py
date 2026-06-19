from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.services.analytics_domain_service import AnalyticsDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

_service = AnalyticsDomainService()


class AddRecordRequest(BaseModel):
    project_id: str = Field(default="default")
    domain: str = Field(..., min_length=1)
    record: dict[str, Any]


@router.get("/design", response_model=ApiResponse[dict])
async def get_design_metrics(project_id: str | None = None):
    metrics = _service.query_design_metrics(project_id)
    return ApiResponse(data=metrics)


@router.get("/manufacturing", response_model=ApiResponse[dict])
async def get_manufacturing_metrics(project_id: str | None = None):
    metrics = _service.query_manufacturing_metrics(project_id)
    return ApiResponse(data=metrics)


@router.get("/quality", response_model=ApiResponse[dict])
async def get_quality_metrics(project_id: str | None = None):
    metrics = _service.query_quality_metrics(project_id)
    return ApiResponse(data=metrics)


@router.get("/traceability", response_model=ApiResponse[dict])
async def get_traceability_metrics(project_id: str | None = None):
    metrics = _service.query_traceability_metrics(project_id)
    return ApiResponse(data=metrics)


@router.get("/supply-chain", response_model=ApiResponse[dict])
async def get_supply_chain_metrics(project_id: str | None = None):
    metrics = _service.query_supply_chain_metrics(project_id)
    return ApiResponse(data=metrics)


@router.get("/cross-domain", response_model=ApiResponse[dict])
async def get_cross_domain_analysis(project_id: str | None = None):
    analysis = _service.cross_domain_analysis(project_id)
    return ApiResponse(data=analysis)


@router.post("/records", response_model=ApiResponse[dict])
async def add_record(body: AddRecordRequest):
    domain_map = {
        "design": _service.add_design_record,
        "manufacturing": _service.add_manufacturing_record,
        "quality": _service.add_quality_record,
        "traceability": _service.add_trace_record,
        "supply_chain": _service.add_supply_record,
    }
    handler = domain_map.get(body.domain)
    if handler is None:
        return ApiResponse(data={"error": f"Unknown domain: {body.domain}"})
    handler(body.project_id, body.record)
    return ApiResponse(data={"status": "ok"})