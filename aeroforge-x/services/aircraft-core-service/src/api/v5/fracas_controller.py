from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.manufacturing.fracas_service import FRACASService

router = APIRouter(prefix="/api/v5/aircraft-core/fracas", tags=["FRACAS v5"])

_service = FRACASService()


@router.post("/failure-reports")
async def create_failure_report(body: dict[str, Any]):
    report = _service.create_failure_report(
        failure_date=body.get("failure_date", ""),
        component_part_number=body.get("component_part_number", ""),
        failure_mode=body.get("failure_mode", ""),
        failure_effect=body.get("failure_effect", ""),
        severity=body.get("severity", "Minor"),
        aircraft_tail_number=body.get("aircraft_tail_number", ""),
        flight_hours_at_failure=body.get("flight_hours_at_failure", 0.0),
        airworthiness_clause=body.get("airworthiness_clause", ""),
    )
    return report.to_dict()


@router.post("/{report_id}/correlate")
async def correlate_failures(report_id: str):
    try:
        result = _service.correlate_failures(report_id=report_id)
        return {
            "report_id": result.report_id,
            "correlated_reports": result.correlated_reports,
            "common_factors": result.common_factors,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{report_id}/root-cause")
async def perform_root_cause_analysis(report_id: str, body: dict[str, Any]):
    symptoms = body.get("symptoms")
    top_k = body.get("top_k", 5)
    try:
        result = _service.perform_root_cause_analysis(
            report_id=report_id, symptoms=symptoms, top_k=top_k,
        )
        return {
            "report_id": result.report_id,
            "candidates": [
                {
                    "root_cause_id": c.root_cause_id,
                    "name": c.name,
                    "category": c.category,
                    "posterior_probability": c.posterior_probability,
                    "causal_path": c.causal_path,
                }
                for c in result.candidates
            ],
            "analysis_duration_ms": result.analysis_duration_ms,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{report_id}/verify-action")
async def verify_corrective_action(report_id: str, body: dict[str, Any]):
    corrective_action = body.get("corrective_action", "")
    subsequent_failures = body.get("subsequent_failure_count", 0)
    try:
        report = _service.verify_corrective_action(
            report_id=report_id,
            corrective_action=corrective_action,
            subsequent_failure_count=subsequent_failures,
        )
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports")
async def generate_fracas_report():
    summary = _service.generate_fracas_report()
    return {
        "total_reports": summary.total_reports,
        "by_severity": summary.by_severity,
        "by_failure_mode": summary.by_failure_mode,
        "verification_rate": summary.verification_rate,
        "top_root_causes": summary.top_root_causes,
    }


@router.put("/{report_id}/lock")
async def lock_airworthiness_record(report_id: str):
    try:
        report = _service.lock_airworthiness_record(report_id=report_id)
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))