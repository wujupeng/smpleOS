from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ..domain.services.supplier_collaboration_service import SupplierCollaborationService
from ..domain.services.supply_risk_service import SupplyRiskService
from ..domain.services.smart_purchase_service import SmartPurchaseService

router = APIRouter(prefix="/api/v1/supply", tags=["supply-chain-v2"])
_collab_service = SupplierCollaborationService()
_risk_service = SupplyRiskService()
_purchase_service = SmartPurchaseService()


class BuildNetworkRequest(BaseModel):
    tenant_id: str
    project_id: str


class ShareForecastRequest(BaseModel):
    network_id: str
    forecast_data: dict[str, Any] | None = None


class SmartPurchaseRequest(BaseModel):
    tenant_id: str
    project_id: str
    material_requirements: list[dict[str, Any]] | None = None


@router.post("/networks")
async def build_network(req: BuildNetworkRequest):
    network = _collab_service.build_supplier_network(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
    )
    return {"data": network.to_detail_dict()}


@router.get("/networks/{network_id}")
async def get_network(network_id: str):
    network = _collab_service.get_network(network_id)
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    return {"data": network.to_detail_dict()}


@router.post("/networks/{network_id}/share-forecast")
async def share_forecast(network_id: str, req: ShareForecastRequest):
    result = _collab_service.share_demand_forecast(
        network_id=req.network_id,
        forecast_data=req.forecast_data,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Network not found")
    return {"data": result}


@router.get("/suppliers/{supplier_id}/performance")
async def get_supplier_performance(supplier_id: str, network_id: str = ""):
    result = _collab_service.track_supplier_performance(
        network_id=network_id,
        supplier_id=supplier_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"data": result}


@router.get("/networks/{network_id}/capacity")
async def get_capacity_status(network_id: str):
    result = _collab_service.manage_supplier_capacity(network_id)
    if not result:
        raise HTTPException(status_code=404, detail="Network not found")
    return {"data": result}


# --- Risk APIs ---

@router.get("/risks/alerts")
async def get_risk_alerts(network_id: str | None = None):
    alerts = _risk_service.get_active_alerts(network_id)
    return {"data": [a.to_dict() for a in alerts]}


@router.get("/risks/{alert_id}")
async def get_risk_alert(alert_id: str):
    alert = _risk_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"data": alert.to_detail_dict()}


@router.post("/risks/{alert_id}/mitigate")
async def mitigate_risk(alert_id: str):
    alert = _risk_service.mitigate_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"data": alert.to_dict()}


@router.get("/risks/assessment")
async def assess_risk_impact(alert_id: str):
    result = _risk_service.assess_risk_impact(alert_id)
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"data": result}


@router.post("/risks/{alert_id}/mitigation-plan")
async def generate_mitigation_plan(alert_id: str):
    result = _risk_service.generate_mitigation_plan(alert_id)
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"data": result}


# --- Smart Purchase APIs ---

@router.post("/smart-purchase/generate")
async def generate_smart_purchase(req: SmartPurchaseRequest):
    result = _purchase_service.generate_smart_purchase_order(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        material_requirements=req.material_requirements,
    )
    return {"data": result}


@router.post("/smart-purchase/optimize-timing")
async def optimize_purchase_timing(req: SmartPurchaseRequest):
    result = _purchase_service.optimize_purchase_timing(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
    )
    return {"data": result}