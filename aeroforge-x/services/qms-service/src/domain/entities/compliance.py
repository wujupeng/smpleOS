from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class ComplianceStandard(str, Enum):
    FAR_23 = "FAR-23"
    FAR_25 = "FAR-25"
    CCAR_23 = "CCAR-23"
    CCAR_25 = "CCAR-25"
    CS_23 = "CS-23"
    CS_25 = "CS-25"
    DO_178C = "DO-178C"
    DO_254 = "DO-254"
    AS9100 = "AS9100"
    NADCAP = "NADCAP"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_ASSESSED = "not_assessed"
    WAIVER_GRANTED = "waiver_granted"


class CheckSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFORMATIONAL = "informational"


class CheckCategory(str, Enum):
    DESIGN = "design"
    MANUFACTURING = "manufacturing"
    QUALITY = "quality"
    AIRWORTHINESS = "airworthiness"
    TRACEABILITY = "traceability"
    DOCUMENTATION = "documentation"
    MATERIAL = "material"
    STRUCTURAL = "structural"
    SYSTEMS = "systems"


@dataclass
class ComplianceRequirement:
    requirement_id: str
    standard: ComplianceStandard
    clause: str
    description: str
    category: CheckCategory
    severity: CheckSeverity
    mandatory: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "standard": self.standard.value,
            "clause": self.clause,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "mandatory": self.mandatory,
        }


@dataclass
class ComplianceCheckResult:
    requirement_id: str
    status: ComplianceStatus
    evidence: str = ""
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    checked_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "status": self.status.value,
            "evidence": self.evidence,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "checked_at": self.checked_at.isoformat(),
            "checked_by": self.checked_by,
        }


class ComplianceCheck(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_model: str,
        standards: list[ComplianceStandard],
        check_type: CheckCategory = CheckCategory.DESIGN,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.aircraft_model = aircraft_model
        self.standards = standards
        self.check_type = check_type
        self.results: list[ComplianceCheckResult] = []
        self.overall_status = ComplianceStatus.NOT_ASSESSED
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None
        self.report_id: str | None = None

    def add_result(self, result: ComplianceCheckResult) -> None:
        self.results.append(result)
        self._update_overall_status()

    def _update_overall_status(self) -> None:
        if not self.results:
            self.overall_status = ComplianceStatus.NOT_ASSESSED
            return

        statuses = [r.status for r in self.results]
        if any(s == ComplianceStatus.NON_COMPLIANT for s in statuses):
            mandatory_non_compliant = any(
                r.status == ComplianceStatus.NON_COMPLIANT
                for r in self.results
            )
            self.overall_status = ComplianceStatus.NON_COMPLIANT
        elif any(s == ComplianceStatus.PARTIALLY_COMPLIANT for s in statuses):
            self.overall_status = ComplianceStatus.PARTIALLY_COMPLIANT
        elif all(s == ComplianceStatus.COMPLIANT or s == ComplianceStatus.WAIVER_GRANTED for s in statuses):
            self.overall_status = ComplianceStatus.COMPLIANT
        else:
            self.overall_status = ComplianceStatus.PARTIALLY_COMPLIANT

    def complete(self) -> None:
        self.completed_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="compliance.check_completed",
            aggregate_id=self.id,
            payload={
                "tenant_id": self.tenant_id,
                "project_id": self.project_id,
                "overall_status": self.overall_status.value,
                "total_checks": len(self.results),
                "non_compliant": sum(1 for r in self.results if r.status == ComplianceStatus.NON_COMPLIANT),
            },
        ))

    def get_summary(self) -> dict[str, Any]:
        status_counts = {}
        for result in self.results:
            status_counts[result.status.value] = status_counts.get(result.status.value, 0) + 1

        critical_findings = [
            r for r in self.results
            if r.status == ComplianceStatus.NON_COMPLIANT
        ]

        return {
            "total_requirements": len(self.results),
            "status_counts": status_counts,
            "overall_status": self.overall_status.value,
            "critical_findings_count": len(critical_findings),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "aircraft_model": self.aircraft_model,
            "standards": [s.value for s in self.standards],
            "check_type": self.check_type.value,
            "overall_status": self.overall_status.value,
            "results": [r.to_dict() for r in self.results],
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "summary": self.get_summary(),
        }


@dataclass
class ComplianceReport:
    report_id: str
    tenant_id: str
    project_id: str
    aircraft_model: str
    standards: list[ComplianceStandard]
    overall_status: ComplianceStatus
    design_compliance: dict[str, Any]
    manufacturing_compliance: dict[str, Any]
    quality_compliance: dict[str, Any]
    traceability_compliance: dict[str, Any]
    non_compliant_items: list[dict[str, Any]]
    recommendations: list[str]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    generated_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "aircraft_model": self.aircraft_model,
            "standards": [s.value for s in self.standards],
            "overall_status": self.overall_status.value,
            "design_compliance": self.design_compliance,
            "manufacturing_compliance": self.manufacturing_compliance,
            "quality_compliance": self.quality_compliance,
            "traceability_compliance": self.traceability_compliance,
            "non_compliant_items": self.non_compliant_items,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat(),
            "generated_by": self.generated_by,
        }