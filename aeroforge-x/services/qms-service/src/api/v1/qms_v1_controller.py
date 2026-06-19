from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.entities.v1.qms_v1_entities import (
    FMEAAnalysis, FRACASRecord, ReliabilityPrediction, LifePrediction,
    FMEAService, FRACASService, ReliabilityService,
)

router = APIRouter()

_fmea_service = FMEAService()
_fracas_service = FRACASService()
_reliability_service = ReliabilityService()

_fmea_analyses: dict[str, FMEAAnalysis] = {}
_fracas_records: dict[str, FRACASRecord] = {}


@router.post("/fmea/analyses")
async def create_fmea(request: dict[str, Any]):
    analysis = _fmea_service.create_analysis(
        fmea_type=request.get("fmea_type", "dfmea"),
        component_id=request.get("component_id"),
        component_name=request.get("component_name"),
        created_by=request.get("created_by"),
    )
    _fmea_analyses[analysis.analysis_id] = analysis
    return {"analysis_id": analysis.analysis_id, "fmea_type": analysis.fmea_type, "status": analysis.status}


@router.post("/fmea/analyses/{analysis_id}/failure-modes")
async def add_failure_mode(analysis_id: str, request: dict[str, Any]):
    a = _fmea_analyses.get(analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
    mode = _fmea_service.add_failure_mode(
        a, request["failure_description"], request.get("severity", 5),
        request.get("occurrence", 5), request.get("detection", 5),
        request.get("is_safety_critical", False),
    )
    return {"mode_id": mode.mode_id, "rpn": mode.rpn, "is_safety_critical": mode.is_safety_critical}


@router.get("/fmea/analyses/{analysis_id}")
async def get_fmea_analysis(analysis_id: str):
    a = _fmea_analyses.get(analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {
        "analysis_id": a.analysis_id, "fmea_type": a.fmea_type,
        "highest_rpn": a.highest_rpn, "failure_modes_count": len(a.failure_modes),
        "status": a.status,
        "failure_modes": [
            {"mode_id": m.mode_id, "description": m.failure_description,
             "s": m.severity, "o": m.occurrence, "d": m.detection, "rpn": m.rpn,
             "is_safety_critical": m.is_safety_critical}
            for m in a.failure_modes
        ],
    }


@router.post("/fracas/reports")
async def create_fracas(request: dict[str, Any]):
    record = _fracas_service.create_failure_report(
        description=request["failure_description"],
        component=request.get("affected_component"),
        serial_number=request.get("serial_number"),
        reported_by=request.get("reported_by"),
        is_safety_critical=request.get("is_safety_critical", False),
    )
    _fracas_records[record.record_id] = record
    return {"record_id": record.record_id, "status": record.status}


@router.post("/fracas/reports/{record_id}/root-cause")
async def record_root_cause(record_id: str, request: dict[str, Any]):
    r = _fracas_records.get(record_id)
    if not r:
        raise HTTPException(status_code=404, detail="Record not found")
    _fracas_service.record_root_cause(r, request["root_cause"])
    return {"record_id": record_id, "status": r.status}


@router.post("/fracas/reports/{record_id}/corrective-action")
async def add_corrective_action(record_id: str, request: dict[str, Any]):
    r = _fracas_records.get(record_id)
    if not r:
        raise HTTPException(status_code=404, detail="Record not found")
    action = _fracas_service.add_corrective_action(r, request["action_description"], request.get("responsible"))
    return {"action_id": action.action_id, "status": action.status}


@router.post("/fracas/reports/{record_id}/verify")
async def verify_corrective_action(record_id: str, request: dict[str, Any]):
    r = _fracas_records.get(record_id)
    if not r:
        raise HTTPException(status_code=404, detail="Record not found")
    _fracas_service.verify_corrective_action(r, request["action_id"], request["verified_by"], request["effectiveness"])
    return {"record_id": record_id, "status": r.status}


@router.post("/reliability/predict-mtbf")
async def predict_mtbf(request: dict[str, Any]):
    pred = _reliability_service.predict_mtbf(
        component_id=request["component_id"],
        total_operating_hours=float(request.get("total_operating_hours", 10000)),
        total_failures=int(request.get("total_failures", 0)),
        confidence_level=float(request.get("confidence_level", 0.90)),
    )
    return {"prediction_id": pred.prediction_id, "mtbf_hours": pred.mtbf_hours,
            "failure_rate": pred.failure_rate_per_million_hours, "confidence_interval": pred.confidence_interval}


@router.post("/reliability/predict-life")
async def predict_life(request: dict[str, Any]):
    pred = _reliability_service.predict_remaining_life(
        component_id=request["component_id"],
        serial_number=request.get("serial_number"),
        total_life_hours=float(request.get("total_life_hours", 10000)),
        consumed_hours=float(request.get("consumed_hours", 5000)),
        warning_threshold_hours=float(request.get("warning_threshold_hours", 100)),
    )
    return {"prediction_id": pred.prediction_id, "remaining_hours": pred.remaining_useful_life_hours,
            "consumption_pct": pred.consumption_pct, "status": pred.status,
            "maintenance_suggestion": pred.maintenance_suggestion}