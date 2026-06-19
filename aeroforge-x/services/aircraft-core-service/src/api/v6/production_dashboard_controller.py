from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.digital_factory.production_dashboard_service import (
    ProductionDashboardService,
    AGVDetail,
)

router = APIRouter(prefix="/api/v6/aircraft-core", tags=["Production Dashboard v6"])

_dashboard_service = ProductionDashboardService()


@router.get("/production-dashboard/oee/{equipment_id}")
async def get_equipment_oee(equipment_id: str):
    oee = _dashboard_service.getEquipmentOEE(equipment_id=equipment_id)
    return oee.to_dict()


@router.get("/production-dashboard/agv-fleet")
async def get_agv_fleet_status():
    status = _dashboard_service.getAGVFleetStatus()
    return status.to_dict()


@router.post("/production-dashboard/bottleneck-detect")
async def detect_bottleneck(body: dict[str, Any]):
    line_id = body.get("line_id", "")
    _dashboard_service.updateOperationUtilization("op-1", 0.95)
    _dashboard_service.updateOperationUtilization("op-2", 0.75)
    _dashboard_service.updateOperationUtilization("op-3", 0.60)
    bottleneck = _dashboard_service.detectBottleneck(line_id=line_id)
    if bottleneck:
        return bottleneck.to_dict()
    return {"bottleneck_detected": False}


@router.post("/production-dashboard/oee-compute")
async def compute_oee(body: dict[str, Any]):
    equipment_id = body.get("equipment_id", "")
    oee = _dashboard_service.computeOEE(
        equipment_id=equipment_id,
        planned_time=body.get("planned_time", 480),
        run_time=body.get("run_time", 420),
        ideal_cycle_time=body.get("ideal_cycle_time", 1.0),
        actual_cycle_time=body.get("actual_cycle_time", 1.1),
        total_pieces=body.get("total_pieces", 380),
        good_pieces=body.get("good_pieces", 370),
    )
    return oee.to_dict()


@router.post("/production-dashboard/agv-update")
async def update_agv_status(body: dict[str, Any]):
    agv = AGVDetail(
        agv_id=body.get("agv_id", ""),
        location=body.get("location", ""),
        task_status=body.get("task_status", "Idle"),
        battery_level=body.get("battery_level", 100.0),
        collision_avoidance_status=body.get("collision_avoidance_status", "Clear"),
    )
    _dashboard_service.updateAGVStatus(agv=agv)
    return {"updated": True, "agv_id": agv.agv_id}