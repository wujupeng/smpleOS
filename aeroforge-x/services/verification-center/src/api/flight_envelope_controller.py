from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.domain.entities.flight_envelope_analysis import FlightEnvelopeAnalysis
from src.domain.services.flight_envelope_engine import FlightEnvelopeEngine

router = APIRouter()
_engine = FlightEnvelopeEngine()
_store: dict[str, FlightEnvelopeAnalysis] = {}


@router.post("/analyze")
async def analyze_flight_envelope(request: dict[str, Any]):
    analysis = _engine.run_full_analysis(request)
    _store[analysis.analysis_id] = analysis
    return {
        "analysis_id": analysis.analysis_id,
        "limit_speeds": {
            "vs1_ms": analysis.limit_speeds.vs1_ms,
            "vs0_ms": analysis.limit_speeds.vs0_ms,
            "va_ms": analysis.limit_speeds.va_ms,
            "vc_ms": analysis.limit_speeds.vc_ms,
            "vd_ms": analysis.limit_speeds.vd_ms,
            "vne_ms": analysis.limit_speeds.vne_ms,
        },
        "limit_load_factors": {
            "n_max_positive": analysis.limit_load_factors.n_max_positive,
            "n_max_negative": analysis.limit_load_factors.n_max_negative,
        },
        "vn_diagram": [
            {"speed_ms": p.speed_ms, "load_factor": p.load_factor, "label": p.label}
            for p in analysis.vn_diagram
        ],
        "gust_envelope": [
            {"speed_ms": p.speed_ms, "load_factor": p.load_factor, "label": p.label}
            for p in analysis.gust_envelope
        ],
        "violations": [
            {"type": v.violation_type, "speed_ms": v.speed_ms, "load_factor": v.load_factor,
             "description": v.description, "severity": v.severity}
            for v in analysis.violations
        ],
        "is_airworthy": analysis.is_airworthy,
        "status": analysis.status,
    }


@router.get("/{analysis_id}")
async def get_flight_envelope_analysis(analysis_id: str):
    analysis = _store.get(analysis_id)
    if not analysis:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
    return {
        "analysis_id": analysis.analysis_id,
        "is_airworthy": analysis.is_airworthy,
        "violations_count": len(analysis.violations),
        "status": analysis.status,
    }