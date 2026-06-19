"""AeroForge-X v5.0 FRACASService

Failure Reporting, Analysis, and Corrective Action System.
Supports failure report creation, correlation analysis, Bayesian root cause
reasoning via Neo4j causal graph, corrective action verification, and
airworthiness record locking.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"


class VerificationStatus(str, Enum):
    PENDING = "Pending"
    VERIFIED = "Verified"
    NOT_EFFECTIVE = "NotEffective"


@dataclass
class FailureReport:
    report_id: str
    failure_date: str
    component_part_number: str
    failure_mode: str
    failure_effect: str
    severity: Severity
    aircraft_tail_number: str
    flight_hours_at_failure: float
    root_cause: str = ""
    corrective_action: str = ""
    verification_status: VerificationStatus = VerificationStatus.PENDING
    airworthiness_clause: str = ""
    locked: bool = False
    causal_graph_ref: str = ""

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "failure_date": self.failure_date,
            "component_part_number": self.component_part_number,
            "failure_mode": self.failure_mode,
            "failure_effect": self.failure_effect,
            "severity": self.severity.value,
            "aircraft_tail_number": self.aircraft_tail_number,
            "flight_hours_at_failure": self.flight_hours_at_failure,
            "root_cause": self.root_cause,
            "corrective_action": self.corrective_action,
            "verification_status": self.verification_status.value,
            "airworthiness_clause": self.airworthiness_clause,
            "locked": self.locked,
            "causal_graph_ref": self.causal_graph_ref,
        }


@dataclass(frozen=True)
class CandidateRootCause:
    root_cause_id: str
    name: str
    category: str
    posterior_probability: float
    causal_path: list[str]


@dataclass(frozen=True)
class RootCauseResult:
    report_id: str
    candidates: list[CandidateRootCause]
    analysis_duration_ms: float


@dataclass(frozen=True)
class CorrelationResult:
    report_id: str
    correlated_reports: list[dict]
    common_factors: list[str]


@dataclass(frozen=True)
class FRACASReportSummary:
    total_reports: int
    by_severity: dict[str, int]
    by_failure_mode: dict[str, int]
    verification_rate: float
    top_root_causes: list[dict]


@dataclass
class CausalGraphEngine:
    engine_id: str
    graph_id: str
    bayesian_model_ref: str = ""

    def compute_posterior(
        self,
        symptoms: list[str],
        prior_probabilities: dict[str, float],
        likelihoods: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        posteriors: dict[str, float] = {}
        total = 0.0

        for cause_id, prior in prior_probabilities.items():
            likelihood = 1.0
            for symptom in symptoms:
                if cause_id in likelihoods and symptom in likelihoods[cause_id]:
                    likelihood *= likelihoods[cause_id][symptom]
                else:
                    likelihood *= 0.01

            unnormalized = prior * likelihood
            posteriors[cause_id] = unnormalized
            total += unnormalized

        if total > 0:
            for cause_id in posteriors:
                posteriors[cause_id] /= total

        return posteriors


_CAUSAL_GRAPH_PRIORS: dict[str, float] = {
    "RC-001": 0.25,
    "RC-002": 0.20,
    "RC-003": 0.15,
    "RC-004": 0.15,
    "RC-005": 0.10,
    "RC-006": 0.10,
    "RC-007": 0.05,
}

_CAUSAL_GRAPH_LIKELIHOODS: dict[str, dict[str, float]] = {
    "RC-001": {"vibration": 0.8, "overtemperature": 0.3, "performance_degradation": 0.6},
    "RC-002": {"vibration": 0.4, "overtemperature": 0.9, "performance_degradation": 0.5},
    "RC-003": {"vibration": 0.2, "overtemperature": 0.1, "performance_degradation": 0.7},
    "RC-004": {"vibration": 0.6, "overtemperature": 0.5, "performance_degradation": 0.3},
    "RC-005": {"vibration": 0.1, "overtemperature": 0.7, "performance_degradation": 0.4},
    "RC-006": {"vibration": 0.3, "overtemperature": 0.2, "performance_degradation": 0.8},
    "RC-007": {"vibration": 0.5, "overtemperature": 0.4, "performance_degradation": 0.2},
}

_ROOT_CAUSE_NAMES: dict[str, tuple[str, str]] = {
    "RC-001": ("Bearing Wear", "ManufacturingProcess"),
    "RC-002": ("Cooling System Failure", "DesignParameter"),
    "RC-003": ("Material Fatigue", "MaterialLot"),
    "RC-004": ("Misalignment", "ManufacturingProcess"),
    "RC-005": ("Inadequate Lubrication", "DesignParameter"),
    "RC-006": ("Corrosion", "MaterialLot"),
    "RC-007": ("Foreign Object Damage", "Operational"),
}


class FRACASService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._reports: dict[str, FailureReport] = {}
        self._causal_engine = CausalGraphEngine(
            engine_id=f"CGE-{uuid.uuid4().hex[:8].upper()}",
            graph_id="FRACAS-Causal-Graph-v1",
        )
        self._priors = dict(_CAUSAL_GRAPH_PRIORS)
        self._likelihoods = dict(_CAUSAL_GRAPH_LIKELIHOODS)
        self._rca_config: dict = {}

    def create_failure_report(
        self,
        failure_date: str,
        component_part_number: str,
        failure_mode: str,
        failure_effect: str,
        severity: str,
        aircraft_tail_number: str,
        flight_hours_at_failure: float,
        airworthiness_clause: str = "",
    ) -> FailureReport:
        report_id = f"FR-{uuid.uuid4().hex[:8].upper()}"

        report = FailureReport(
            report_id=report_id,
            failure_date=failure_date,
            component_part_number=component_part_number,
            failure_mode=failure_mode,
            failure_effect=failure_effect,
            severity=Severity(severity),
            aircraft_tail_number=aircraft_tail_number,
            flight_hours_at_failure=flight_hours_at_failure,
            airworthiness_clause=airworthiness_clause,
            causal_graph_ref=f"neo4j://failure_report/{report_id}",
        )

        self._reports[report_id] = report
        return report

    def correlate_failures(self, report_id: str) -> CorrelationResult:
        report = self._reports.get(report_id)
        if report is None:
            raise ValueError(f"Report {report_id} not found")

        correlated: list[dict] = []
        common_factors: list[str] = []

        for other_id, other in self._reports.items():
            if other_id == report_id:
                continue

            factors: list[str] = []
            if other.component_part_number == report.component_part_number:
                factors.append("same_component")
            if other.failure_mode == report.failure_mode:
                factors.append("same_failure_mode")
            if other.aircraft_tail_number == report.aircraft_tail_number:
                factors.append("same_aircraft")

            if factors:
                correlated.append({
                    "report_id": other_id,
                    "common_factors": factors,
                    "component_part_number": other.component_part_number,
                    "failure_mode": other.failure_mode,
                })
                common_factors.extend(factors)

        return CorrelationResult(
            report_id=report_id,
            correlated_reports=correlated,
            common_factors=list(set(common_factors)),
        )

    def perform_root_cause_analysis(
        self,
        report_id: str,
        symptoms: list[str] | None = None,
        top_k: int = 5,
    ) -> RootCauseResult:
        start = time.time()

        report = self._reports.get(report_id)
        if report is None:
            raise ValueError(f"Report {report_id} not found")

        if symptoms is None:
            symptoms = self._infer_symptoms(report)

        posteriors = self._causal_engine.compute_posterior(
            symptoms=symptoms,
            prior_probabilities=self._priors,
            likelihoods=self._likelihoods,
        )

        sorted_causes = sorted(posteriors.items(), key=lambda x: x[1], reverse=True)

        candidates: list[CandidateRootCause] = []
        for cause_id, prob in sorted_causes[:top_k]:
            name, category = _ROOT_CAUSE_NAMES.get(cause_id, ("Unknown", "Unknown"))
            candidates.append(CandidateRootCause(
                root_cause_id=cause_id,
                name=name,
                category=category,
                posterior_probability=prob,
                causal_path=[report_id, "symptom", "failure_mode", cause_id],
            ))

        elapsed = (time.time() - start) * 1000

        if report and candidates:
            report.root_cause = candidates[0].name

        return RootCauseResult(
            report_id=report_id,
            candidates=candidates,
            analysis_duration_ms=elapsed,
        )

    def verify_corrective_action(
        self,
        report_id: str,
        corrective_action: str,
        subsequent_failure_count: int = 0,
    ) -> FailureReport:
        report = self._reports.get(report_id)
        if report is None:
            raise ValueError(f"Report {report_id} not found")

        if report.locked:
            raise ValueError(f"Report {report_id} is locked — cannot modify")

        report.corrective_action = corrective_action

        if subsequent_failure_count == 0:
            report.verification_status = VerificationStatus.VERIFIED
        else:
            report.verification_status = VerificationStatus.NOT_EFFECTIVE

        return report

    def generate_fracas_report(self) -> FRACASReportSummary:
        reports = list(self._reports.values())

        by_severity: dict[str, int] = {}
        by_mode: dict[str, int] = {}
        verified = 0

        root_cause_counts: dict[str, int] = {}
        for r in reports:
            by_severity[r.severity.value] = by_severity.get(r.severity.value, 0) + 1
            by_mode[r.failure_mode] = by_mode.get(r.failure_mode, 0) + 1
            if r.verification_status == VerificationStatus.VERIFIED:
                verified += 1
            if r.root_cause:
                root_cause_counts[r.root_cause] = root_cause_counts.get(r.root_cause, 0) + 1

        top_causes = sorted(root_cause_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return FRACASReportSummary(
            total_reports=len(reports),
            by_severity=by_severity,
            by_failure_mode=by_mode,
            verification_rate=verified / len(reports) if reports else 0.0,
            top_root_causes=[{"cause": c, "count": n} for c, n in top_causes],
        )

    def lock_airworthiness_record(self, report_id: str) -> FailureReport:
        report = self._reports.get(report_id)
        if report is None:
            raise ValueError(f"Report {report_id} not found")

        if not report.airworthiness_clause:
            raise ValueError("Cannot lock report without airworthiness clause")

        report.locked = True
        return report

    def get_failure_report(self, report_id: str) -> Optional[FailureReport]:
        return self._reports.get(report_id)

    def configure_rca_algorithm(self, config: dict) -> None:
        self._rca_config = config
        if "priors" in config:
            self._priors.update(config["priors"])
        if "likelihoods" in config:
            for cause_id, likelihoods in config["likelihoods"].items():
                if cause_id in self._likelihoods:
                    self._likelihoods[cause_id].update(likelihoods)

    def _infer_symptoms(self, report: FailureReport) -> list[str]:
        symptoms: list[str] = []
        effect_lower = report.failure_effect.lower()
        mode_lower = report.failure_mode.lower()

        if "vibrat" in effect_lower or "vibrat" in mode_lower:
            symptoms.append("vibration")
        if "temperature" in effect_lower or "heat" in effect_lower or "thermal" in mode_lower:
            symptoms.append("overtemperature")
        if "performance" in effect_lower or "degrad" in effect_lower or "loss" in mode_lower:
            symptoms.append("performance_degradation")

        if not symptoms:
            symptoms = ["performance_degradation"]

        return symptoms