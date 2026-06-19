from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.tenant import TenantPlan, TenantStatus
from ..domain.services.tenant_domain_service import TenantDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant Management"])

_service = TenantDomainService()


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_]+$")
    plan: str = Field(default="starter")


class UpdateTenantRequest(BaseModel):
    name: str | None = None


class UpdatePlanRequest(BaseModel):
    plan: str = Field(..., description="starter | professional | enterprise")


class SuspendTenantRequest(BaseModel):
    reason: str = ""


class CheckQuotaRequest(BaseModel):
    resource: str
    current: int | float = 0


@router.post("", response_model=ApiResponse[dict])
async def create_tenant(body: CreateTenantRequest):
    try:
        plan = TenantPlan(body.plan)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {body.plan}")
    try:
        tenant = _service.create_tenant(name=body.name, code=body.code, plan=plan)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ApiResponse(data=tenant.to_dict())


@router.get("", response_model=ApiResponse[dict])
async def list_tenants(status: str | None = None):
    tenant_status = TenantStatus(status) if status else None
    tenants = _service.list_tenants(tenant_status)
    return ApiResponse(data={
        "total": len(tenants),
        "tenants": [t.to_dict() for t in tenants],
    })


@router.get("/{tenant_id}", response_model=ApiResponse[dict])
async def get_tenant(tenant_id: str):
    tenant = _service.get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return ApiResponse(data=tenant.to_dict())


@router.get("/code/{code}", response_model=ApiResponse[dict])
async def get_tenant_by_code(code: str):
    tenant = _service.get_tenant_by_code(code)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return ApiResponse(data=tenant.to_dict())


@router.put("/{tenant_id}", response_model=ApiResponse[dict])
async def update_tenant(tenant_id: str, body: UpdateTenantRequest):
    tenant = _service.update_tenant(tenant_id, name=body.name)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return ApiResponse(data=tenant.to_dict())


@router.put("/{tenant_id}/plan", response_model=ApiResponse[dict])
async def update_tenant_plan(tenant_id: str, body: UpdatePlanRequest):
    try:
        plan = TenantPlan(body.plan)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {body.plan}")
    tenant = _service.update_tenant_plan(tenant_id, plan)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return ApiResponse(data=tenant.to_dict())


@router.post("/{tenant_id}/suspend", response_model=ApiResponse[dict])
async def suspend_tenant(tenant_id: str, body: SuspendTenantRequest):
    tenant = _service.suspend_tenant(tenant_id, reason=body.reason)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return ApiResponse(data=tenant.to_dict())


@router.post("/{tenant_id}/activate", response_model=ApiResponse[dict])
async def activate_tenant(tenant_id: str):
    tenant = _service.activate_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return ApiResponse(data=tenant.to_dict())


@router.post("/{tenant_id}/check-quota", response_model=ApiResponse[dict])
async def check_quota(tenant_id: str, body: CheckQuotaRequest):
    result = _service.check_quota(tenant_id, body.resource, body.current)
    return ApiResponse(data=result)


@router.get("/{tenant_id}/features/{feature_name}", response_model=ApiResponse[dict])
async def check_feature(tenant_id: str, feature_name: str):
    has = _service.has_feature(tenant_id, feature_name)
    return ApiResponse(data={"tenant_id": tenant_id, "feature": feature_name, "enabled": has})