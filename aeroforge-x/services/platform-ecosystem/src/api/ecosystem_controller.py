from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ..domain.services.ecosystem_services import (
    DeveloperPortalService,
    PluginMarketplaceService,
)
from ..domain.services.multi_site_service import MultiSiteService

router = APIRouter(prefix="/api/v1/open", tags=["platform-ecosystem"])
_dev_service = DeveloperPortalService()
_plugin_service = PluginMarketplaceService()
_multi_site_service = MultiSiteService()


class RegisterDeveloperRequest(BaseModel):
    tenant_id: str
    developer_name: str
    email: str
    tier: str = "free"


class CreateApiKeyRequest(BaseModel):
    developer_id: str
    scopes: list[str] | None = None
    rate_limit: int = 1000


class SubmitAppRequest(BaseModel):
    tenant_id: str
    developer_id: str
    name: str
    description: str
    app_type: str = "integration"


class SubmitPluginRequest(BaseModel):
    tenant_id: str
    developer_id: str
    name: str
    description: str
    plugin_type: str = "visualization"
    price_model: str = "free"


class RatePluginRequest(BaseModel):
    score: float


@router.post("/developers/register")
async def register_developer(req: RegisterDeveloperRequest):
    from ..domain.entities.developer_app import DeveloperTier
    try:
        tier = DeveloperTier(req.tier)
    except ValueError:
        tier = DeveloperTier.FREE
    result = _dev_service.register_developer(
        tenant_id=req.tenant_id,
        developer_name=req.developer_name,
        email=req.email,
        tier=tier,
    )
    return {"data": result}


@router.post("/developers/api-keys")
async def create_api_key(req: CreateApiKeyRequest):
    key = _dev_service.create_api_key(
        developer_id=req.developer_id,
        scopes=req.scopes,
        rate_limit=req.rate_limit,
    )
    if not key:
        raise HTTPException(status_code=404, detail="Developer not found")
    return {"data": key.to_dict()}


@router.post("/apps")
async def submit_app(req: SubmitAppRequest):
    app = _dev_service.submit_app(
        tenant_id=req.tenant_id,
        developer_id=req.developer_id,
        name=req.name,
        description=req.description,
        app_type=req.app_type,
    )
    if not app:
        raise HTTPException(status_code=404, detail="Developer not found")
    return {"data": app.to_detail_dict()}


@router.get("/apps/{app_id}/usage")
async def get_app_usage(app_id: str):
    result = _dev_service.track_api_usage(app_id)
    if not result:
        raise HTTPException(status_code=404, detail="App not found")
    return {"data": result}


@router.post("/apps/{app_id}/publish")
async def publish_app(app_id: str):
    app = _dev_service.publish_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return {"data": app.to_dict()}


@router.post("/plugins")
async def submit_plugin(req: SubmitPluginRequest):
    plugin = _plugin_service.submit_plugin(
        tenant_id=req.tenant_id,
        developer_id=req.developer_id,
        name=req.name,
        description=req.description,
        plugin_type=req.plugin_type,
        price_model=req.price_model,
    )
    return {"data": plugin.to_detail_dict()}


@router.get("/plugins")
async def list_plugins(plugin_type: str | None = None, search: str | None = None):
    plugins = _plugin_service.list_plugins(plugin_type=plugin_type, search=search)
    return {"data": [p.to_dict() for p in plugins]}


@router.post("/plugins/{plugin_id}/install")
async def install_plugin(plugin_id: str, tenant_id: str = "default"):
    plugin = _plugin_service.install_plugin(tenant_id=tenant_id, plugin_id=plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found or not published")
    return {"data": plugin.to_dict()}


@router.delete("/plugins/{plugin_id}/install")
async def uninstall_plugin(plugin_id: str, tenant_id: str = "default"):
    plugin = _plugin_service.uninstall_plugin(tenant_id=tenant_id, plugin_id=plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {"data": plugin.to_dict()}


@router.post("/plugins/{plugin_id}/rate")
async def rate_plugin(plugin_id: str, req: RatePluginRequest):
    plugin = _plugin_service.rate_plugin(plugin_id, req.score)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {"data": plugin.to_dict()}


# --- Multi-Site APIs ---

class RegisterSiteRequest(BaseModel):
    tenant_id: str
    name: str
    location: str = ""
    timezone: str = "UTC"
    capacity: float = 1000.0
    specialization: str = ""


class SyncRequest(BaseModel):
    tenant_id: str
    data_type: str = "all"


class DistributeWorkOrderRequest(BaseModel):
    tenant_id: str
    work_order_id: str
    quantity: float = 100


class FailoverRequest(BaseModel):
    tenant_id: str
    failed_site_id: str


@router.post("/platform/sites")
async def register_site(req: RegisterSiteRequest):
    config = _multi_site_service.register_site(
        tenant_id=req.tenant_id,
        name=req.name,
        location=req.location,
        timezone=req.timezone,
        capacity=req.capacity,
        specialization=req.specialization,
    )
    return {"data": config.to_detail_dict()}


@router.get("/platform/sites")
async def list_sites(tenant_id: str):
    sites = _multi_site_service.get_sites(tenant_id)
    return {"data": sites}


@router.post("/platform/sync")
async def sync_data(req: SyncRequest):
    result = _multi_site_service.sync_data_across_sites(
        tenant_id=req.tenant_id,
        data_type=req.data_type,
    )
    return {"data": result}


@router.get("/platform/progress")
async def get_progress(tenant_id: str, project_id: str = ""):
    result = _multi_site_service.aggregate_multi_site_progress(
        tenant_id=tenant_id,
        project_id=project_id,
    )
    return {"data": result}


@router.post("/platform/distribute")
async def distribute_work_order(req: DistributeWorkOrderRequest):
    result = _multi_site_service.distribute_work_order(
        tenant_id=req.tenant_id,
        work_order_id=req.work_order_id,
        quantity=req.quantity,
    )
    return {"data": result}


@router.post("/platform/failover")
async def site_failover(req: FailoverRequest):
    result = _multi_site_service.manage_site_failover(
        tenant_id=req.tenant_id,
        failed_site_id=req.failed_site_id,
    )
    return {"data": result}