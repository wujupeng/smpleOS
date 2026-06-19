from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.audit_log import AuditAction, AuditDetail, AuditResource
from ..domain.services.audit_domain_service import AuditDomainService, AuditQueryFilter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Log"])

_service = AuditDomainService()


class AuditDetailItem(BaseModel):
    field_name: str
    old_value: Any = None
    new_value: Any = None


class RecordAuditRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    action: str = Field(..., description="create|read|update|delete|login|logout|approve|reject|submit|export|share|sync")
    resource_type: str = Field(..., description="tenant|project|design|bom|mes_order|qms_inspection|cae_task|supplier|purchase_order|inventory|spc_chart|schedule|report|user|role|permission")
    resource_id: str = Field(..., min_length=1)
    resource_name: str = ""
    details: list[AuditDetailItem] = []
    ip_address: str = ""
    user_agent: str = ""
    request_id: str = ""


class VerifyIntegrityRequest(BaseModel):
    tenant_id: str | None = None


@router.post("/logs", response_model=ApiResponse[dict])
async def record_audit(body: RecordAuditRequest):
    try:
        action = AuditAction(body.action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {body.action}")
    try:
        resource_type = AuditResource(body.resource_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid resource_type: {body.resource_type}")

    details = [
        AuditDetail(field_name=d.field_name, old_value=d.old_value, new_value=d.new_value)
        for d in body.details
    ]

    log = _service.record(
        tenant_id=body.tenant_id,
        user_id=body.user_id,
        action=action,
        resource_type=resource_type,
        resource_id=body.resource_id,
        resource_name=body.resource_name,
        details=details,
        ip_address=body.ip_address,
        user_agent=body.user_agent,
        request_id=body.request_id,
    )
    return ApiResponse(data=log.to_dict())


@router.get("/logs", response_model=ApiResponse[dict])
async def query_audit_logs(
    tenant_id: str | None = None,
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    parsed_action = None
    if action:
        try:
            parsed_action = AuditAction(action)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    parsed_resource_type = None
    if resource_type:
        try:
            parsed_resource_type = AuditResource(resource_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid resource_type: {resource_type}")

    parsed_start = None
    if start_time:
        try:
            parsed_start = datetime.fromisoformat(start_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format, use ISO 8601")

    parsed_end = None
    if end_time:
        try:
            parsed_end = datetime.fromisoformat(end_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format, use ISO 8601")

    filter_params = AuditQueryFilter(
        tenant_id=tenant_id,
        user_id=user_id,
        action=parsed_action,
        resource_type=parsed_resource_type,
        resource_id=resource_id,
        start_time=parsed_start,
        end_time=parsed_end,
        request_id=request_id,
        ip_address=ip_address,
        page=page,
        page_size=page_size,
    )
    result = _service.query(filter_params)
    return ApiResponse(data=result)


@router.get("/logs/{log_id}", response_model=ApiResponse[dict])
async def get_audit_log(log_id: str):
    log = _service.get_log(log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return ApiResponse(data=log.to_dict())


@router.post("/verify-integrity", response_model=ApiResponse[dict])
async def verify_chain_integrity(body: VerifyIntegrityRequest | None = None):
    tenant_id = body.tenant_id if body else None
    result = _service.verify_chain_integrity(tenant_id)
    return ApiResponse(data=result)


@router.get("/export/csv", response_class=PlainTextResponse)
async def export_audit_csv(
    tenant_id: str | None = None,
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(1000, ge=1, le=10000),
):
    parsed_action = None
    if action:
        try:
            parsed_action = AuditAction(action)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    parsed_resource_type = None
    if resource_type:
        try:
            parsed_resource_type = AuditResource(resource_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid resource_type: {resource_type}")

    parsed_start = None
    if start_time:
        try:
            parsed_start = datetime.fromisoformat(start_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    parsed_end = None
    if end_time:
        try:
            parsed_end = datetime.fromisoformat(end_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    filter_params = AuditQueryFilter(
        tenant_id=tenant_id,
        user_id=user_id,
        action=parsed_action,
        resource_type=parsed_resource_type,
        start_time=parsed_start,
        end_time=parsed_end,
        page=page,
        page_size=page_size,
    )
    csv_content = _service.export_csv(filter_params)
    return PlainTextResponse(content=csv_content, media_type="text/csv")


@router.get("/export/json", response_model=ApiResponse[dict])
async def export_audit_json(
    tenant_id: str | None = None,
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(1000, ge=1, le=10000),
):
    parsed_action = None
    if action:
        try:
            parsed_action = AuditAction(action)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    parsed_resource_type = None
    if resource_type:
        try:
            parsed_resource_type = AuditResource(resource_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid resource_type: {resource_type}")

    parsed_start = None
    if start_time:
        try:
            parsed_start = datetime.fromisoformat(start_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    parsed_end = None
    if end_time:
        try:
            parsed_end = datetime.fromisoformat(end_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    filter_params = AuditQueryFilter(
        tenant_id=tenant_id,
        user_id=user_id,
        action=parsed_action,
        resource_type=parsed_resource_type,
        start_time=parsed_start,
        end_time=parsed_end,
        page=page,
        page_size=page_size,
    )
    json_content = _service.export_json(filter_params)
    import json as json_lib
    return ApiResponse(data=json_lib.loads(json_content))


@router.get("/statistics/{tenant_id}", response_model=ApiResponse[dict])
async def get_audit_statistics(tenant_id: str):
    result = _service.get_statistics(tenant_id)
    return ApiResponse(data=result)