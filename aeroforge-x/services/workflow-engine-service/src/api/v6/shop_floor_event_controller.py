from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.digital_factory.shop_floor_event_emitter_service import (
    ShopFloorEventEmitterService,
    EventFilter,
    ShopFloorEventType,
)

router = APIRouter(prefix="/api/v6/workflow-engine", tags=["Shop Floor Events v6"])

_event_service = ShopFloorEventEmitterService()


@router.post("/shop-floor-events/equipment-status")
async def emit_equipment_status_event(body: dict[str, Any]):
    equipment_id = body.get("equipment_id", "")
    new_status = body.get("new_status", "")
    receipt = _event_service.emitEquipmentStatusChange(
        equipment_id=equipment_id, new_status=new_status
    )
    return receipt.to_dict()


@router.post("/shop-floor-events/operation")
async def emit_operation_event(body: dict[str, Any]):
    operation_id = body.get("operation_id", "")
    event_type = body.get("event_type", "complete")
    receipt = _event_service.emitOperationEvent(
        operation_id=operation_id, event_type=event_type
    )
    return receipt.to_dict()


@router.post("/shop-floor-events/quality-alert")
async def emit_quality_alert(body: dict[str, Any]):
    equipment_id = body.get("equipment_id", "")
    alert_data = body.get("alert_data", {})
    receipt = _event_service.emitQualityAlert(equipment_id=equipment_id, alert_data=alert_data)
    return receipt.to_dict()


@router.post("/shop-floor-events/deviation-alert")
async def emit_deviation_alert(body: dict[str, Any]):
    equipment_id = body.get("equipment_id", "")
    deviation_data = body.get("deviation_data", {})
    receipt = _event_service.emitDeviationAlert(
        equipment_id=equipment_id, deviation_data=deviation_data
    )
    return receipt.to_dict()


@router.post("/shop-floor-events/playback")
async def playback_events(body: dict[str, Any]):
    event_filter = None
    if body.get("filter"):
        f = body["filter"]
        event_filter = EventFilter(
            event_type=ShopFloorEventType(f["event_type"]) if f.get("event_type") else None,
            source_equipment_id=f.get("source_equipment_id", ""),
            time_from=f.get("time_from", 0),
            time_to=f.get("time_to", 0),
        )
    time_window_s = body.get("time_window_s")
    events = _event_service.playbackEvents(event_filter=event_filter, time_window_s=time_window_s)
    return {"events": [e.to_dict() for e in events], "total": len(events)}