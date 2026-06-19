from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from aeroforge_db.pg import get_session
from aeroforge_common.domain.responses import ApiResponse

from ..application.qms_application_service import QmsApplicationService
from ..infrastructure.qms_repository import QmsRepository

router = APIRouter(prefix="/api/v1/qms", tags=["QMS"])


class GeneratePlanRequest(BaseModel):
    item_code: str
    work_order_id: str | None = None


class RecordResultRequest(BaseModel):
    item_code: str
    inspector: str
    measurements: dict[str, Any] = Field(default_factory=dict)
    criteria: dict[str, Any] = Field(default_factory=dict)
    plan_id: str | None = None


class CreateCapaRequest(BaseModel):
    inspection_record_id: str | None = None


class ExecuteCapaRequest(BaseModel):
    root_cause: str
    corrective_action: str
    preventive_action: str


class VerifyCapaRequest(BaseModel):
    result: str = Field(..., pattern="^(pass|fail|marginal)$")


def _get_service(session: AsyncSession = Depends(get_session)) -> QmsApplicationService:
    return QmsApplicationService(QmsRepository(session))


@router.post("/iqc/plans", response_model=ApiResponse[dict])
async def generate_iqc_plan(body: GeneratePlanRequest, service: QmsApplicationService = Depends(_get_service)):
    result = await service.generate_iqc_plan(body.item_code, body.work_order_id)
    return ApiResponse(data=result)


@router.post("/iqc/results", response_model=ApiResponse[dict])
async def record_iqc_result(body: RecordResultRequest, service: QmsApplicationService = Depends(_get_service)):
    result = await service.record_iqc_result(body.item_code, body.inspector, body.measurements, body.criteria, body.plan_id)
    return ApiResponse(data=result)


@router.get("/iqc/status/{item_code}", response_model=ApiResponse[dict])
async def check_iqc_status(item_code: str, service: QmsApplicationService = Depends(_get_service)):
    result = await service.check_iqc_status(item_code)
    return ApiResponse(data=result)


@router.post("/fqc/plans", response_model=ApiResponse[dict])
async def generate_fqc_plan(body: GeneratePlanRequest, service: QmsApplicationService = Depends(_get_service)):
    result = await service.generate_fqc_plan(body.item_code, body.work_order_id)
    return ApiResponse(data=result)


@router.post("/fqc/results", response_model=ApiResponse[dict])
async def record_fqc_result(body: RecordResultRequest, service: QmsApplicationService = Depends(_get_service)):
    result = await service.record_fqc_result(body.item_code, body.inspector, body.measurements, body.criteria, body.plan_id)
    return ApiResponse(data=result)


@router.post("/capa", response_model=ApiResponse[dict])
async def create_capa(body: CreateCapaRequest, service: QmsApplicationService = Depends(_get_service)):
    result = await service.create_capa(body.inspection_record_id, created_by="system")
    return ApiResponse(data=result)


@router.put("/capa/{capa_id}/execute", response_model=ApiResponse[dict])
async def execute_capa(capa_id: str, body: ExecuteCapaRequest, service: QmsApplicationService = Depends(_get_service)):
    result = await service.execute_capa(capa_id, body.root_cause, body.corrective_action, body.preventive_action)
    if result is None:
        raise HTTPException(status_code=404, detail=f"CAPA '{capa_id}' not found")
    return ApiResponse(data=result)


@router.put("/capa/{capa_id}/verify", response_model=ApiResponse[dict])
async def verify_capa(capa_id: str, body: VerifyCapaRequest, service: QmsApplicationService = Depends(_get_service)):
    result = await service.verify_capa(capa_id, body.result)
    if result is None:
        raise HTTPException(status_code=404, detail=f"CAPA '{capa_id}' not found")
    return ApiResponse(data=result)