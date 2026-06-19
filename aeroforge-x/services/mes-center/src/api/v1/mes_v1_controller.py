from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.entities.v1.traveler_record import TravelerRecord
from src.domain.entities.v1.ndt_inspection import NDTInspection
from src.domain.entities.v1.tool_calibration import ToolCalibration
from src.domain.services.v1.mes_v1_services import TravelerService, NDTService, ToolCalibrationService

router = APIRouter()

_traveler_service = TravelerService()
_ndt_service = NDTService()
_calibration_service = ToolCalibrationService()

_travelers: dict[str, TravelerRecord] = {}
_inspections: dict[str, NDTInspection] = {}


@router.post("/travelers")
async def create_traveler(request: dict[str, Any]):
    traveler = _traveler_service.create_traveler(
        work_order_id=request["work_order_id"],
        serial_number=request["serial_number"],
        process_step=request["process_step"],
        operator_id=request.get("operator_id"),
        curing_oven=request.get("curing_oven"),
    )
    _travelers[traveler.traveler_id] = traveler
    return {"traveler_id": traveler.traveler_id, "status": traveler.status, "serial_number": traveler.serial_number}


@router.get("/travelers/{traveler_id}")
async def get_traveler(traveler_id: str):
    t = _travelers.get(traveler_id)
    if not t:
        raise HTTPException(status_code=404, detail="Traveler not found")
    return {
        "traveler_id": t.traveler_id, "work_order_id": t.work_order_id,
        "serial_number": t.serial_number, "process_step": t.process_step,
        "status": t.status, "temperature_readings": len(t.temperature_profile),
        "quality_inspector": t.quality_inspector, "confirmed_at": t.confirmed_at.isoformat() if t.confirmed_at else None,
    }


@router.post("/travelers/{traveler_id}/temperature-profile")
async def record_temperature(traveler_id: str, request: dict[str, Any]):
    t = _travelers.get(traveler_id)
    if not t:
        raise HTTPException(status_code=404, detail="Traveler not found")
    reading = _traveler_service.record_temperature_profile(
        t, Decimal(str(request["temperature_c"])), Decimal(str(request["target_temp_c"])),
        Decimal(str(request.get("tolerance_c", 5))), Decimal(str(request.get("duration_s", 0))),
    )
    return {"within_tolerance": reading.is_within_tolerance, "deviation_c": float(reading.deviation_c), "status": t.status}


@router.post("/travelers/{traveler_id}/confirm")
async def confirm_traveler(traveler_id: str, request: dict[str, Any]):
    t = _travelers.get(traveler_id)
    if not t:
        raise HTTPException(status_code=404, detail="Traveler not found")
    _traveler_service.confirm_traveler(t, request["inspector_id"])
    return {"traveler_id": traveler_id, "status": t.status}


@router.post("/travelers/{traveler_id}/finalize")
async def finalize_traveler(traveler_id: str):
    t = _travelers.get(traveler_id)
    if not t:
        raise HTTPException(status_code=404, detail="Traveler not found")
    try:
        _traveler_service.finalize_traveler(t)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    events = t.clear_events()
    return {"traveler_id": traveler_id, "status": t.status, "events": events}


@router.post("/ndt/inspections")
async def create_ndt_inspection(request: dict[str, Any]):
    insp = _ndt_service.create_inspection(
        serial_number=request["serial_number"],
        method=request.get("method", "ultrasonic"),
        traveler_ref=request.get("traveler_ref"),
        tool_calibration_ref=request.get("tool_calibration_ref"),
        tool_calibration_valid=request.get("tool_calibration_valid", True),
    )
    _inspections[insp.inspection_id] = insp
    return {"inspection_id": insp.inspection_id, "status": insp.status}


@router.get("/ndt/inspections/{inspection_id}")
async def get_ndt_inspection(inspection_id: str):
    insp = _inspections.get(inspection_id)
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return {"inspection_id": insp.inspection_id, "result": insp.result, "status": insp.status, "method": insp.inspection_method}


@router.post("/ndt/inspections/{inspection_id}/result")
async def record_ndt_result(inspection_id: str, request: dict[str, Any]):
    insp = _inspections.get(inspection_id)
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found")
    try:
        _ndt_service.record_result(insp, request["result"], request.get("defect_description"), request.get("inspector_id"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    judgment = _ndt_service.judge_result(insp)
    return {"inspection_id": inspection_id, "result": insp.result, "judgment": judgment}


@router.post("/tool-calibrations")
async def record_calibration(request: dict[str, Any]):
    cal = _calibration_service.record_calibration(
        tool_id=request["tool_id"], tool_name=request["tool_name"],
        calibration_date=request["calibration_date"], next_due_date=request["next_due_date"],
        result=request.get("result", "pass"), uncertainty=request.get("uncertainty"),
        certificate_ref=request.get("certificate_ref"), calibrated_by=request.get("calibrated_by"),
    )
    return {"calibration_id": cal.calibration_id, "tool_id": cal.tool_id, "status": cal.status}


@router.get("/tool-calibrations/expiring")
async def get_expiring_calibrations():
    expiring = _calibration_service.check_calibration_expiry()
    return {"expiring_count": len(expiring), "tools": [{"tool_id": c.tool_id, "tool_name": c.tool_name, "status": c.status} for c in expiring]}


@router.post("/tool-calibrations/{calibration_id}/trace-affected")
async def trace_affected(calibration_id: str):
    affected = _calibration_service.trace_affected_work_orders(calibration_id)
    return {"calibration_id": calibration_id, "affected_work_orders": affected}