"""AeroForge-X v6.0 CertificationComplianceDashboardService

Aggregates certification compliance metrics for dashboard display:
traceability coverage, checklist completion, evidence package status.

REQ-DFX-V6-004
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DashboardPeriod(str, Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"


@dataclass
class TraceabilityCoverageWidget:
    total_requirements: int = 0
    fully_traced: int = 0
    coverage_percentage: float = 0.0
    test_linkage_percentage: float = 0.0
    evidence_linkage_percentage: float = 0.0
    broken_links_count: int = 0
    trend: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_requirements": self.total_requirements,
            "fully_traced": self.fully_traced,
            "coverage_percentage": self.coverage_percentage,
            "test_linkage_percentage": self.test_linkage_percentage,
            "evidence_linkage_percentage": self.evidence_linkage_percentage,
            "broken_links_count": self.broken_links_count,
            "trend": self.trend,
        }


@dataclass
class ChecklistCompletionWidget:
    total_checklists: int = 0
    completed: int = 0
    in_progress: int = 0
    not_started: int = 0
    completion_percentage: float = 0.0
    by_regulation_type: dict = field(default_factory=dict)
    trend: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_checklists": self.total_checklists,
            "completed": self.completed,
            "in_progress": self.in_progress,
            "not_started": self.not_started,
            "completion_percentage": self.completion_percentage,
            "by_regulation_type": self.by_regulation_type,
            "trend": self.trend,
        }


@dataclass
class EvidencePackageStatusWidget:
    total_packages: int = 0
    complete: int = 0
    incomplete: int = 0
    locked: int = 0
    submitted: int = 0
    draft: int = 0
    gap_items_count: int = 0
    trend: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_packages": self.total_packages,
            "complete": self.complete,
            "incomplete": self.incomplete,
            "locked": self.locked,
            "submitted": self.submitted,
            "draft": self.draft,
            "gap_items_count": self.gap_items_count,
            "trend": self.trend,
        }


@dataclass
class ComplianceDashboard:
    dashboard_id: str
    project_id: str
    period: DashboardPeriod
    traceability: TraceabilityCoverageWidget = field(default_factory=TraceabilityCoverageWidget)
    checklists: ChecklistCompletionWidget = field(default_factory=ChecklistCompletionWidget)
    evidence_packages: EvidencePackageStatusWidget = field(default_factory=EvidencePackageStatusWidget)
    overall_compliance_score: float = 0.0
    generated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "dashboard_id": self.dashboard_id,
            "project_id": self.project_id,
            "period": self.period.value,
            "traceability": self.traceability.to_dict(),
            "checklists": self.checklists.to_dict(),
            "evidence_packages": self.evidence_packages.to_dict(),
            "overall_compliance_score": self.overall_compliance_score,
            "generated_at": self.generated_at,
        }


class CertificationComplianceDashboardService:

    def __init__(self) -> None:
        self._dashboards: dict[str, ComplianceDashboard] = {}

    def generateDashboard(
        self,
        project_id: str,
        period: DashboardPeriod,
        traceability_data: dict | None = None,
        checklist_data: dict | None = None,
        evidence_data: dict | None = None,
    ) -> ComplianceDashboard:
        dashboard_id = f"DASH-{project_id}-{uuid.uuid4().hex[:6]}"

        trace_widget = self._build_traceability_widget(traceability_data or {})
        checklist_widget = self._build_checklist_widget(checklist_data or {})
        evidence_widget = self._build_evidence_widget(evidence_data or {})

        overall_score = (
            trace_widget.coverage_percentage * 0.4
            + checklist_widget.completion_percentage * 0.3
            + (evidence_widget.complete / max(evidence_widget.total_packages, 1)) * 100 * 0.3
        )

        dashboard = ComplianceDashboard(
            dashboard_id=dashboard_id,
            project_id=project_id,
            period=period,
            traceability=trace_widget,
            checklists=checklist_widget,
            evidence_packages=evidence_widget,
            overall_compliance_score=round(overall_score, 2),
        )

        self._dashboards[dashboard_id] = dashboard
        return dashboard

    def _build_traceability_widget(self, data: dict) -> TraceabilityCoverageWidget:
        total = data.get("total_requirements", 0)
        fully_traced = data.get("fully_traced", 0)
        coverage = (fully_traced / total * 100) if total > 0 else 100.0

        return TraceabilityCoverageWidget(
            total_requirements=total,
            fully_traced=fully_traced,
            coverage_percentage=round(coverage, 2),
            test_linkage_percentage=data.get("test_linkage_percentage", 0.0),
            evidence_linkage_percentage=data.get("evidence_linkage_percentage", 0.0),
            broken_links_count=data.get("broken_links_count", 0),
        )

    def _build_checklist_widget(self, data: dict) -> ChecklistCompletionWidget:
        total = data.get("total_checklists", 0)
        completed = data.get("completed", 0)
        in_progress = data.get("in_progress", 0)
        not_started = total - completed - in_progress
        completion = (completed / total * 100) if total > 0 else 0.0

        return ChecklistCompletionWidget(
            total_checklists=total,
            completed=completed,
            in_progress=in_progress,
            not_started=not_started,
            completion_percentage=round(completion, 2),
            by_regulation_type=data.get("by_regulation_type", {}),
        )

    def _build_evidence_widget(self, data: dict) -> EvidencePackageStatusWidget:
        total = data.get("total_packages", 0)
        complete = data.get("complete", 0)
        locked = data.get("locked", 0)
        submitted = data.get("submitted", 0)

        return EvidencePackageStatusWidget(
            total_packages=total,
            complete=complete,
            incomplete=total - complete,
            locked=locked,
            submitted=submitted,
            draft=total - submitted,
            gap_items_count=data.get("gap_items_count", 0),
        )

    def getDashboard(self, dashboard_id: str) -> Optional[ComplianceDashboard]:
        return self._dashboards.get(dashboard_id)

    def getProjectDashboards(self, project_id: str) -> list[ComplianceDashboard]:
        return [
            d for d in self._dashboards.values() if d.project_id == project_id
        ]