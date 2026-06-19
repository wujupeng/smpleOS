from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from aeroforge_integrations.erp.adapter import ERPConnectionConfig, ERPType
from aeroforge_integrations.erp.sync_service import ERPDataSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations/erp", tags=["ERP Integration"])

_services: dict[str, ERPDataSyncService] = {}


class ConfigureERPRequest(BaseModel):
    config_id: str = Field(default="default")
    erp_type: str = Field(..., description="sap|oracle|generic")
    base_url: str = Field(..., min_length=1)
    username: str = ""
    password: str = ""
    api_key: str = ""


class SyncRequest(BaseModel):
    config_id: str = Field(default="default")
    data_type: str = Field(..., description="material_master|bom|work_order|cost|inventory")
    material_code: str | None = None
    items: list[dict[str, Any]] = []


@router.post("/configure", response_model=ApiResponse[dict])
async def configure_erp(body: ConfigureERPRequest):
    try:
        erp_type = ERPType(body.erp_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid ERP type: {body.erp_type}")

    config = ERPConnectionConfig(
        erp_type=erp_type,
        base_url=body.base_url,
        username=body.username,
        password=body.password,
        api_key=body.api_key,
    )

    service = ERPDataSyncService(config)
    result = service.connect()
    if result.get("connected"):
        _services[body.config_id] = service

    return ApiResponse(data=result)


@router.post("/sync", response_model=ApiResponse[dict])
async def trigger_sync(body: SyncRequest):
    service = _services.get(body.config_id)
    if service is None:
        raise HTTPException(status_code=404, detail="ERP connection not configured")

    if body.data_type == "material_master":
        record = service.sync_material_master(body.material_code)
    elif body.data_type == "bom":
        record = service.sync_bom_to_erp(body.items)
    elif body.data_type == "work_order":
        record = service.sync_work_order_to_erp(body.items)
    elif body.data_type == "cost":
        record = service.sync_cost_from_erp(body.material_code)
    elif body.data_type == "inventory":
        record = service.sync_inventory_from_erp(body.material_code)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid data_type: {body.data_type}")

    return ApiResponse(data=record.to_dict())


@router.get("/sync-status", response_model=ApiResponse[dict])
async def get_sync_status(config_id: str = "default"):
    service = _services.get(config_id)
    if service is None:
        raise HTTPException(status_code=404, detail="ERP connection not configured")
    return ApiResponse(data=service.get_sync_status())


@router.get("/config", response_model=ApiResponse[dict])
async def get_erp_config(config_id: str = "default"):
    service = _services.get(config_id)
    if service is None:
        raise HTTPException(status_code=404, detail="ERP connection not configured")
    return ApiResponse(data=service.get_config())


@router.get("/test-connection", response_model=ApiResponse[dict])
async def test_erp_connection(config_id: str = "default"):
    service = _services.get(config_id)
    if service is None:
        raise HTTPException(status_code=404, detail="ERP connection not configured")
    return ApiResponse(data=service.test_connection())