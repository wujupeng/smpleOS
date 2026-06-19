from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TestResult:
    test_result_id: str
    test_case_id: str
    execution_status: str = "passed"
    execution_duration_ms: float = 0.0
    code_version: str = ""
    environment: str = ""
    service_id: str = ""
    module_name: str = ""
    result_data: dict[str, Any] = field(default_factory=dict)
    evidence_locked: bool = False
    checksum: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class CoverageRecord:
    record_id: str
    service_id: str
    code_version: str = ""
    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    function_coverage: float = 0.0
    module_coverages: dict[str, dict[str, float]] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class BenchmarkRecord:
    record_id: str
    kpi_name: str
    kpi_value: float
    kpi_unit: str = ""
    code_version: str = ""
    environment: str = ""
    service_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class CoverageTarget:
    target_id: str
    scope: str = "module"
    scope_name: str = ""
    criticality: str = "normal"
    line_coverage_target: float = 80.0
    branch_coverage_target: float = 70.0


@dataclass
class BenchmarkTarget:
    target_id: str
    kpi_name: str
    service_criticality: str = "normal"
    target_value: float = 0.0
    regression_threshold_pct: float = 20.0


@dataclass
class RegressionFlag:
    test_case_id: str
    from_version: str
    to_version: str
    previous_status: str
    current_status: str
    flagged_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notified_team: str = ""


@dataclass
class TraceabilityLink:
    link_id: str
    test_case_id: str
    test_result_id: str = ""
    airworthiness_clause: str = ""
    compliance_method: str = ""
    verification_evidence_id: str = ""
    link_status: str = "active"


@dataclass
class EvidenceReport:
    clause: str
    clause_title: str = ""
    compliance_method: str = ""
    evidence_list: list[dict[str, Any]] = field(default_factory=list)
    test_results_summary: dict[str, Any] = field(default_factory=dict)
    compliance_conclusion: str = ""
    gaps: list[str] = field(default_factory=list)


class TestResultCollector:

    def __init__(self) -> None:
        self._results: list[TestResult] = []
        self._checksums: set[str] = set()

    def collect(self, data: str, format_type: str = "pytest_json") -> list[TestResult]:
        if format_type == "junit_xml":
            return self._parse_junit_xml(data)
        elif format_type == "pytest_json":
            return self._parse_pytest_json(data)
        return []

    def collect_coverage(self, data: str, service_id: str = "", code_version: str = "") -> CoverageRecord | None:
        try:
            coverage_data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None

        totals = coverage_data.get("totals", {})
        line_cov = totals.get("covered_lines", 0) / max(totals.get("num_statements", 1), 1) * 100
        branch_cov = totals.get("covered_branches", 0) / max(totals.get("num_branches", 1), 1) * 100
        func_cov = totals.get("covered_functions", 0) / max(totals.get("num_functions", 1), 1) * 100

        module_coverages: dict[str, dict[str, float]] = {}
        files = coverage_data.get("files", {})
        for file_path, file_data in files.items():
            summary = file_data.get("summary", {})
            mod_line = summary.get("covered_lines", 0) / max(summary.get("num_statements", 1), 1) * 100
            mod_branch = summary.get("covered_branches", 0) / max(summary.get("num_branches", 1), 1) * 100
            module_coverages[file_path] = {"line_coverage": mod_line, "branch_coverage": mod_branch}

        record = CoverageRecord(
            record_id=f"cov-{hashlib.sha256(data.encode()).hexdigest()[:12]}",
            service_id=service_id,
            code_version=code_version,
            line_coverage=line_cov,
            branch_coverage=branch_cov,
            function_coverage=func_cov,
            module_coverages=module_coverages,
        )
        return record

    def collect_benchmark(self, kpi_name: str, kpi_value: float, kpi_unit: str = "", code_version: str = "", environment: str = "", service_id: str = "") -> BenchmarkRecord:
        return BenchmarkRecord(
            record_id=f"bm-{hashlib.sha256(f'{kpi_name}:{kpi_value}'.encode()).hexdigest()[:12]}",
            kpi_name=kpi_name,
            kpi_value=kpi_value,
            kpi_unit=kpi_unit,
            code_version=code_version,
            environment=environment,
            service_id=service_id,
        )

    def validate_format(self, data: str, format_type: str) -> bool:
        if format_type == "junit_xml":
            try:
                ET.fromstring(data)
                return True
            except ET.ParseError:
                return False
        elif format_type == "pytest_json":
            try:
                json.loads(data)
                return True
            except (json.JSONDecodeError, TypeError):
                return False
        return False

    def _compute_checksum(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def _is_duplicate(self, checksum: str) -> bool:
        if checksum in self._checksums:
            return True
        self._checksums.add(checksum)
        return False

    def _parse_junit_xml(self, data: str) -> list[TestResult]:
        results = []
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            return results

        for testcase in root.iter("testcase"):
            case_id = testcase.get("name", "unknown")
            classname = testcase.get("classname", "")
            duration = float(testcase.get("time", 0)) * 1000

            status = "passed"
            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped = testcase.find("skipped")
            if failure is not None:
                status = "failed"
            elif error is not None:
                status = "error"
            elif skipped is not None:
                status = "skipped"

            checksum = self._compute_checksum(f"{case_id}:{classname}:{status}")
            if self._is_duplicate(checksum):
                continue

            result = TestResult(
                test_result_id=f"tr-{checksum[:12]}",
                test_case_id=case_id,
                execution_status=status,
                execution_duration_ms=duration,
                module_name=classname,
                checksum=checksum,
            )
            results.append(result)
            self._results.append(result)

        return results

    def _parse_pytest_json(self, data: str) -> list[TestResult]:
        results = []
        try:
            report = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return results

        tests = report.get("tests", [])
        for test in tests:
            case_id = test.get("nodeid", "unknown")
            outcome = test.get("outcome", "unknown")
            duration = test.get("duration", 0) * 1000

            status_map = {"passed": "passed", "failed": "failed", "skipped": "skipped", "xfailed": "expected_failure"}
            status = status_map.get(outcome, "unknown")

            checksum = self._compute_checksum(f"{case_id}:{outcome}")
            if self._is_duplicate(checksum):
                continue

            result = TestResult(
                test_result_id=f"tr-{checksum[:12]}",
                test_case_id=case_id,
                execution_status=status,
                execution_duration_ms=duration,
                checksum=checksum,
            )
            results.append(result)
            self._results.append(result)

        return results

    @property
    def results(self) -> list[TestResult]:
        return list(self._results)


class CoverageAggregator:

    def __init__(self) -> None:
        self._records: list[CoverageRecord] = []
        self._targets: list[CoverageTarget] = []

    def add_record(self, record: CoverageRecord) -> None:
        self._records.append(record)

    def add_target(self, target: CoverageTarget) -> None:
        self._targets.append(target)

    def aggregate_module_coverage(self, service_id: str) -> dict[str, dict[str, float]]:
        service_records = [r for r in self._records if r.service_id == service_id]
        if not service_records:
            return {}
        latest = service_records[-1]
        return latest.module_coverages

    def aggregate_service_coverage(self, service_id: str) -> dict[str, float]:
        service_records = [r for r in self._records if r.service_id == service_id]
        if not service_records:
            return {"line_coverage": 0.0, "branch_coverage": 0.0, "function_coverage": 0.0}
        latest = service_records[-1]
        return {
            "line_coverage": latest.line_coverage,
            "branch_coverage": latest.branch_coverage,
            "function_coverage": latest.function_coverage,
        }

    def aggregate_system_coverage(self) -> dict[str, float]:
        if not self._records:
            return {"line_coverage": 0.0, "branch_coverage": 0.0, "function_coverage": 0.0}

        services = set(r.service_id for r in self._records)
        total_line = 0.0
        total_branch = 0.0
        total_func = 0.0
        count = 0

        for svc in services:
            svc_cov = self.aggregate_service_coverage(svc)
            total_line += svc_cov["line_coverage"]
            total_branch += svc_cov["branch_coverage"]
            total_func += svc_cov["function_coverage"]
            count += 1

        if count == 0:
            return {"line_coverage": 0.0, "branch_coverage": 0.0, "function_coverage": 0.0}

        return {
            "line_coverage": total_line / count,
            "branch_coverage": total_branch / count,
            "function_coverage": total_func / count,
        }

    def generate_coverage_report(self, service_id: str | None = None) -> dict[str, Any]:
        if service_id:
            return {
                "service_id": service_id,
                "service_coverage": self.aggregate_service_coverage(service_id),
                "module_coverage": self.aggregate_module_coverage(service_id),
                "timestamp": datetime.utcnow().isoformat(),
            }
        return {
            "system_coverage": self.aggregate_system_coverage(),
            "services": {
                svc: self.aggregate_service_coverage(svc)
                for svc in set(r.service_id for r in self._records)
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    def check_coverage_threshold(self) -> list[dict[str, Any]]:
        warnings_list: list[dict[str, Any]] = []
        for target in self._targets:
            if target.scope == "service":
                cov = self.aggregate_service_coverage(target.scope_name)
                if cov["line_coverage"] < target.line_coverage_target:
                    warnings_list.append({
                        "scope": target.scope_name,
                        "type": "line_coverage",
                        "current": cov["line_coverage"],
                        "target": target.line_coverage_target,
                        "criticality": target.criticality,
                    })
                if cov["branch_coverage"] < target.branch_coverage_target:
                    warnings_list.append({
                        "scope": target.scope_name,
                        "type": "branch_coverage",
                        "current": cov["branch_coverage"],
                        "target": target.branch_coverage_target,
                        "criticality": target.criticality,
                    })
        return warnings_list


class RegressionDetector:

    def __init__(self) -> None:
        self._results_by_version: dict[str, dict[str, str]] = {}

    def register_version_results(self, version: str, results: dict[str, str]) -> None:
        self._results_by_version[version] = results

    def compare_versions(self, from_version: str, to_version: str) -> dict[str, Any]:
        from_results = self._results_by_version.get(from_version, {})
        to_results = self._results_by_version.get(to_version, {})

        new_failures = self.detect_new_failures(from_results, to_results)
        new_passes = self.detect_new_passes(from_results, to_results)

        return {
            "from_version": from_version,
            "to_version": to_version,
            "new_failures": len(new_failures),
            "new_passes": len(new_passes),
            "from_total": len(from_results),
            "to_total": len(to_results),
            "from_pass_rate": self._pass_rate(from_results),
            "to_pass_rate": self._pass_rate(to_results),
        }

    def detect_new_failures(self, from_results: dict[str, str], to_results: dict[str, str]) -> list[str]:
        failures = []
        for case_id, status in to_results.items():
            if status in ("failed", "error"):
                prev = from_results.get(case_id, "")
                if prev not in ("failed", "error"):
                    failures.append(case_id)
        return failures

    def detect_new_passes(self, from_results: dict[str, str], to_results: dict[str, str]) -> list[str]:
        passes = []
        for case_id, status in to_results.items():
            if status == "passed":
                prev = from_results.get(case_id, "")
                if prev in ("failed", "error"):
                    passes.append(case_id)
        return passes

    def compute_pass_rate_trend(self) -> list[dict[str, Any]]:
        trend = []
        for version in sorted(self._results_by_version.keys()):
            results = self._results_by_version[version]
            trend.append({
                "version": version,
                "pass_rate": self._pass_rate(results),
                "total": len(results),
                "passed": sum(1 for s in results.values() if s == "passed"),
                "failed": sum(1 for s in results.values() if s in ("failed", "error")),
            })
        return trend

    def auto_flag_regression(self, from_version: str, to_version: str) -> list[RegressionFlag]:
        from_results = self._results_by_version.get(from_version, {})
        to_results = self._results_by_version.get(to_version, {})

        flags = []
        for case_id, status in to_results.items():
            if status in ("failed", "error"):
                prev = from_results.get(case_id, "")
                if prev == "passed":
                    flags.append(RegressionFlag(
                        test_case_id=case_id,
                        from_version=from_version,
                        to_version=to_version,
                        previous_status=prev,
                        current_status=status,
                    ))
        return flags

    @staticmethod
    def _pass_rate(results: dict[str, str]) -> float:
        if not results:
            return 0.0
        passed = sum(1 for s in results.values() if s == "passed")
        return passed / len(results) * 100


class BenchmarkTracker:

    def __init__(self) -> None:
        self._records: list[BenchmarkRecord] = []
        self._targets: list[BenchmarkTarget] = []

    def add_target(self, target: BenchmarkTarget) -> None:
        self._targets.append(target)

    def record_benchmark(self, record: BenchmarkRecord) -> None:
        self._records.append(record)

    def generate_trend_report(self, kpi_name: str | None = None) -> dict[str, Any]:
        records = self._records
        if kpi_name:
            records = [r for r in records if r.kpi_name == kpi_name]

        if not records:
            return {"kpi_name": kpi_name or "all", "trend": [], "current": None}

        by_kpi: dict[str, list[BenchmarkRecord]] = {}
        for r in records:
            by_kpi.setdefault(r.kpi_name, []).append(r)

        trend_data = {}
        for kpi, kpi_records in by_kpi.items():
            sorted_records = sorted(kpi_records, key=lambda r: r.timestamp)
            trend_data[kpi] = [
                {"version": r.code_version, "value": r.kpi_value, "timestamp": r.timestamp}
                for r in sorted_records
            ]

        return {
            "kpi_name": kpi_name or "all",
            "trend": trend_data,
            "current": {kpi: vals[-1]["value"] for kpi, vals in trend_data.items() if vals},
        }

    def detect_performance_regression(self, kpi_name: str, threshold_pct: float = 20.0) -> list[dict[str, Any]]:
        kpi_records = sorted(
            [r for r in self._records if r.kpi_name == kpi_name],
            key=lambda r: r.timestamp,
        )
        if len(kpi_records) < 2:
            return []

        regressions = []
        for i in range(1, len(kpi_records)):
            prev = kpi_records[i - 1].kpi_value
            curr = kpi_records[i].kpi_value
            if prev > 0:
                change_pct = (curr - prev) / prev * 100
                if change_pct > threshold_pct:
                    regressions.append({
                        "kpi_name": kpi_name,
                        "previous_value": prev,
                        "current_value": curr,
                        "change_pct": change_pct,
                        "version": kpi_records[i].code_version,
                    })
        return regressions

    def check_benchmark_targets(self) -> list[dict[str, Any]]:
        results = []
        for target in self._targets:
            kpi_records = [r for r in self._records if r.kpi_name == target.kpi_name]
            if not kpi_records:
                results.append({
                    "kpi_name": target.kpi_name,
                    "status": "no_data",
                    "target": target.target_value,
                })
                continue

            latest = max(kpi_records, key=lambda r: r.timestamp)
            met = latest.kpi_value <= target.target_value if target.target_value > 0 else True
            results.append({
                "kpi_name": target.kpi_name,
                "status": "met" if met else "not_met",
                "current": latest.kpi_value,
                "target": target.target_value,
                "service_criticality": target.service_criticality,
            })
        return results


class AirworthinessEvidenceChain:

    def __init__(self) -> None:
        self._links: list[TraceabilityLink] = []
        self._locked_evidence: set[str] = set()
        self._clause_risks: dict[str, str] = {}

    def create_traceability_link(
        self,
        test_case_id: str,
        airworthiness_clause: str,
        compliance_method: str = "",
        test_result_id: str = "",
        verification_evidence_id: str = "",
    ) -> TraceabilityLink:
        link_id = f"tl-{hashlib.sha256(f'{test_case_id}:{airworthiness_clause}'.encode()).hexdigest()[:12]}"
        link = TraceabilityLink(
            link_id=link_id,
            test_case_id=test_case_id,
            test_result_id=test_result_id,
            airworthiness_clause=airworthiness_clause,
            compliance_method=compliance_method,
            verification_evidence_id=verification_evidence_id,
        )
        self._links.append(link)
        return link

    def generate_evidence_report(self, clause: str) -> EvidenceReport:
        clause_links = [l for l in self._links if l.airworthiness_clause == clause]

        evidence_list = [
            {
                "link_id": l.link_id,
                "test_case_id": l.test_case_id,
                "test_result_id": l.test_result_id,
                "compliance_method": l.compliance_method,
                "verification_evidence_id": l.verification_evidence_id,
                "status": l.link_status,
            }
            for l in clause_links
        ]

        test_results_summary = {
            "total_links": len(clause_links),
            "active_links": sum(1 for l in clause_links if l.link_status == "active"),
        }

        gaps = self._detect_clause_gaps(clause, clause_links)

        conclusion = "compliant"
        if gaps:
            conclusion = "gaps_found"
        if clause in self._clause_risks:
            conclusion = "compliance_risk"

        return EvidenceReport(
            clause=clause,
            compliance_method=clause_links[0].compliance_method if clause_links else "",
            evidence_list=evidence_list,
            test_results_summary=test_results_summary,
            compliance_conclusion=conclusion,
            gaps=gaps,
        )

    def check_evidence_integrity(self, test_result_id: str) -> bool:
        for link in self._links:
            if link.test_result_id == test_result_id:
                expected = hashlib.sha256(f"{link.test_case_id}:{link.airworthiness_clause}".encode()).hexdigest()[:12]
                if link.link_id != f"tl-{expected}":
                    return False
        return True

    def detect_evidence_gaps(self) -> list[dict[str, Any]]:
        clauses = set(l.airworthiness_clause for l in self._links)
        gaps = []
        for clause in clauses:
            clause_links = [l for l in self._links if l.airworthiness_clause == clause]
            clause_gaps = self._detect_clause_gaps(clause, clause_links)
            if clause_gaps:
                gaps.append({
                    "clause": clause,
                    "gaps": clause_gaps,
                    "total_links": len(clause_links),
                })
        return gaps

    def lock_evidence(self, test_result_id: str) -> bool:
        if test_result_id in self._locked_evidence:
            return False
        has_clause = any(l.test_result_id == test_result_id and l.airworthiness_clause for l in self._links)
        if not has_clause:
            return False
        self._locked_evidence.add(test_result_id)
        return True

    def unlock_evidence(self, test_result_id: str, authorized: bool = False) -> bool:
        if not authorized:
            return False
        self._locked_evidence.discard(test_result_id)
        return True

    def mark_clause_risk(self, test_case_id: str, clause: str) -> None:
        self._clause_risks[clause] = f"Test case {test_case_id} failed — clause marked as compliance risk"

    def _detect_clause_gaps(self, clause: str, links: list[TraceabilityLink]) -> list[str]:
        gaps = []
        if not links:
            gaps.append(f"No traceability links for clause {clause}")
        for link in links:
            if not link.test_result_id:
                gaps.append(f"Missing test result for test case {link.test_case_id}")
            if not link.compliance_method:
                gaps.append(f"Missing compliance method for test case {link.test_case_id}")
        return gaps

    @property
    def links(self) -> list[TraceabilityLink]:
        return list(self._links)