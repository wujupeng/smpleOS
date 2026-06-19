from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.domain.entities.stability_analysis import StabilityAnalysis
from src.domain.services.stability_engine import StabilityEngine

router = APIRouter()
_engine = StabilityEngine()
_store: dict[str, StabilityAnalysis] = {}


@router.post("/analyze")
async def analyze_stability(request: dict[str, Any]):
    analysis = _engine.run_full_analysis(request)
    _store[analysis.analysis_id] = analysis
    return {
        "analysis_id": analysis.analysis_id,
        "longitudinal": {
            "static_margin_pct_mac": analysis.longitudinal_result.static_margin_pct_mac,
            "neutral_point_pct_mac": analysis.longitudinal_result.neutral_point_pct_mac,
            "pitch_stiffness_derivative": analysis.longitudinal_result.pitch_stiffness_derivative,
            "is_stable": analysis.longitudinal_result.is_longitudinally_stable,
        },
        "lateral": {
            "roll_stiffness_derivative": analysis.lateral_result.roll_stiffness_derivative,
            "dutch_roll_damping_ratio": analysis.lateral_result.dutch_roll_damping_ratio,
            "dutch_roll_frequency_hz": analysis.lateral_result.dutch_roll_frequency_hz,
            "is_stable": analysis.lateral_result.is_laterally_stable,
        },
        "directional": {
            "yaw_stiffness_derivative": analysis.directional_result.yaw_stiffness_derivative,
            "weathercock_stability": analysis.directional_result.weathercock_stability,
            "is_stable": analysis.directional_result.is_directionally_stable,
        },
        "is_statically_unstable": analysis.is_statically_unstable,
        "suggestions": [
            {"parameter": s.parameter, "current_value": s.current_value,
             "suggested_value": s.suggested_value, "reason": s.reason}
            for s in analysis.suggestions
        ],
        "status": analysis.status,
    }


@router.get("/{analysis_id}")
async def get_stability_analysis(analysis_id: str):
    analysis = _store.get(analysis_id)
    if not analysis:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
    return {
        "analysis_id": analysis.analysis_id,
        "is_statically_unstable": analysis.is_statically_unstable,
        "longitudinal_stable": analysis.longitudinal_result.is_longitudinally_stable,
        "lateral_stable": analysis.lateral_result.is_laterally_stable,
        "directional_stable": analysis.directional_result.is_directionally_stable,
        "suggestions_count": len(analysis.suggestions),
        "status": analysis.status,
    }