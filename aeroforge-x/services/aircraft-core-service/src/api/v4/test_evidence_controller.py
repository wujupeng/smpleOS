from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.test_evidence.test_evidence_service import (
    AirworthinessEvidenceChain,
    BenchmarkTarget,
    CoverageAggregator,
    CoverageTarget,
    RegressionDetector,
    BenchmarkTracker,
    TestResultCollector,
)

router = APIRouter(prefix="/api/v4/aircraft-core", tags=["Test Evidence v4"])

_collector = TestResultCollector()
_coverage_aggregator = CoverageAggregator()
_regression_detector = RegressionDetector()
_benchmark_tracker = BenchmarkTracker()
_evidence_chain = AirworthinessEvidenceChain()


@router.post("/test-results")
async def submit_test_results(body: dict[str, Any]):
    data = body.get("data", "")
    format_type = body.get("format", "pytest_json")

    if not _collector.validate_format(data, format_type):
        raise HTTPException(status_code=400, detail=f"Invalid {format_type} format")

    results = _collector.collect(data, format_type)
    return {
        "collected_count": len(results),
        "results": [
            {
                "test_result_id": r.test_result_id,
                "test_case_id": r.test_case_id,
                "execution_status": r.execution_status,
                "execution_duration_ms": r.execution_duration_ms,
            }
            for r in results
        ],
    }


@router.post("/test-results/coverage")
async def submit_coverage(body: dict[str, Any]):
    data = body.get("data", "")
    service_id = body.get("service_id", "")
    code_version = body.get("code_version", "")

    record = _collector.collect_coverage(data, service_id, code_version)
    if record is None:
        raise HTTPException(status_code=400, detail="Invalid coverage data format")

    _coverage_aggregator.add_record(record)
    return {
        "record_id": record.record_id,
        "service_id": record.service_id,
        "line_coverage": record.line_coverage,
        "branch_coverage": record.branch_coverage,
        "function_coverage": record.function_coverage,
    }


@router.post("/test-results/benchmarks")
async def submit_benchmarks(body: dict[str, Any]):
    record = _collector.collect_benchmark(
        kpi_name=body.get("kpi_name", ""),
        kpi_value=body.get("kpi_value", 0.0),
        kpi_unit=body.get("kpi_unit", ""),
        code_version=body.get("code_version", ""),
        environment=body.get("environment", ""),
        service_id=body.get("service_id", ""),
    )
    _benchmark_tracker.record_benchmark(record)
    return {
        "record_id": record.record_id,
        "kpi_name": record.kpi_name,
        "kpi_value": record.kpi_value,
    }


@router.get("/test-results")
async def query_test_results(service_id: str | None = None, status: str | None = None):
    results = _collector.results
    if service_id:
        results = [r for r in results if r.service_id == service_id]
    if status:
        results = [r for r in results if r.execution_status == status]
    return {
        "total": len(results),
        "results": [
            {
                "test_result_id": r.test_result_id,
                "test_case_id": r.test_case_id,
                "execution_status": r.execution_status,
                "execution_duration_ms": r.execution_duration_ms,
                "module_name": r.module_name,
            }
            for r in results
        ],
    }


@router.get("/coverage/reports/{service_id}")
async def get_coverage_report(service_id: str):
    return _coverage_aggregator.generate_coverage_report(service_id)


@router.get("/coverage/reports")
async def get_system_coverage_report():
    return _coverage_aggregator.generate_coverage_report()


@router.post("/coverage/targets")
async def set_coverage_target(body: dict[str, Any]):
    target = CoverageTarget(
        target_id=body.get("target_id", ""),
        scope=body.get("scope", "service"),
        scope_name=body.get("scope_name", ""),
        criticality=body.get("criticality", "normal"),
        line_coverage_target=body.get("line_coverage_target", 80.0),
        branch_coverage_target=body.get("branch_coverage_target", 70.0),
    )
    _coverage_aggregator.add_target(target)
    return {"status": "target_set", "target_id": target.target_id}


@router.get("/coverage/warnings")
async def check_coverage_warnings():
    return {"warnings": _coverage_aggregator.check_coverage_threshold()}


@router.post("/regression/compare")
async def compare_versions(body: dict[str, Any]):
    from_version = body.get("from_version", "")
    to_version = body.get("to_version", "")
    if not from_version or not to_version:
        raise HTTPException(status_code=400, detail="from_version and to_version required")
    return _regression_detector.compare_versions(from_version, to_version)


@router.post("/regression/register")
async def register_version_results(body: dict[str, Any]):
    version = body.get("version", "")
    results = body.get("results", {})
    if not version:
        raise HTTPException(status_code=400, detail="version required")
    _regression_detector.register_version_results(version, results)
    return {"status": "registered", "version": version}


@router.get("/regression/trend")
async def get_pass_rate_trend():
    return {"trend": _regression_detector.compute_pass_rate_trend()}


@router.get("/benchmarks/trend")
async def get_benchmark_trend(kpi_name: str | None = None):
    return _benchmark_tracker.generate_trend_report(kpi_name)


@router.post("/benchmarks/targets")
async def set_benchmark_target(body: dict[str, Any]):
    target = BenchmarkTarget(
        target_id=body.get("target_id", ""),
        kpi_name=body.get("kpi_name", ""),
        service_criticality=body.get("service_criticality", "normal"),
        target_value=body.get("target_value", 0.0),
        regression_threshold_pct=body.get("regression_threshold_pct", 20.0),
    )
    _benchmark_tracker.add_target(target)
    return {"status": "target_set", "target_id": target.target_id}


@router.get("/benchmarks/check-targets")
async def check_benchmark_targets():
    return {"results": _benchmark_tracker.check_benchmark_targets()}


@router.post("/evidence/traceability-links")
async def create_traceability_link(body: dict[str, Any]):
    link = _evidence_chain.create_traceability_link(
        test_case_id=body.get("test_case_id", ""),
        airworthiness_clause=body.get("airworthiness_clause", ""),
        compliance_method=body.get("compliance_method", ""),
        test_result_id=body.get("test_result_id", ""),
        verification_evidence_id=body.get("verification_evidence_id", ""),
    )
    return {
        "link_id": link.link_id,
        "test_case_id": link.test_case_id,
        "airworthiness_clause": link.airworthiness_clause,
        "status": "created",
    }


@router.get("/evidence/reports/{clause}")
async def get_evidence_report(clause: str):
    report = _evidence_chain.generate_evidence_report(clause)
    return {
        "clause": report.clause,
        "compliance_method": report.compliance_method,
        "evidence_count": len(report.evidence_list),
        "compliance_conclusion": report.compliance_conclusion,
        "gaps": report.gaps,
    }


@router.get("/evidence/gaps")
async def detect_evidence_gaps():
    return {"gaps": _evidence_chain.detect_evidence_gaps()}


@router.post("/evidence/lock")
async def lock_evidence(body: dict[str, Any]):
    test_result_id = body.get("test_result_id", "")
    success = _evidence_chain.lock_evidence(test_result_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot lock evidence — no associated clause or already locked")
    return {"status": "locked", "test_result_id": test_result_id}


@router.post("/evidence/unlock")
async def unlock_evidence(body: dict[str, Any]):
    test_result_id = body.get("test_result_id", "")
    authorized = body.get("authorized", False)
    success = _evidence_chain.unlock_evidence(test_result_id, authorized)
    if not success:
        raise HTTPException(status_code=403, detail="Not authorized to unlock evidence")
    return {"status": "unlocked", "test_result_id": test_result_id}