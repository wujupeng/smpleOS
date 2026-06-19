from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class ProposalStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    ITERATING = "iterating"


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMarker:
    marker_id: str
    category: str
    description: str
    severity: RiskSeverity = RiskSeverity.MEDIUM
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker_id": self.marker_id,
            "category": self.category,
            "description": self.description,
            "severity": self.severity.value,
            "suggestion": self.suggestion,
        }


@dataclass
class IterationRecord:
    iteration_id: str
    feedback: str
    adjusted_params: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration_id": self.iteration_id,
            "feedback": self.feedback,
            "adjusted_params": self.adjusted_params,
            "timestamp": self.timestamp,
        }


@dataclass
class FeasibilityReport:
    is_feasible: bool = True
    design_rule_violations: list[dict[str, Any]] = field(default_factory=list)
    cae_assessment: dict[str, Any] = field(default_factory=dict)
    parameter_rationality: dict[str, Any] = field(default_factory=dict)
    overall_score: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_feasible": self.is_feasible,
            "design_rule_violations": self.design_rule_violations,
            "cae_assessment": self.cae_assessment,
            "parameter_rationality": self.parameter_rationality,
            "overall_score": round(self.overall_score, 2),
            "summary": self.summary,
        }


@dataclass
class AIProposal:
    id: str = field(default_factory=lambda: str(uuid4()))
    project_id: str = ""
    tenant_id: str = ""
    status: ProposalStatus = ProposalStatus.PENDING_REVIEW
    natural_language_input: str = ""
    parsed_spec: dict[str, Any] = field(default_factory=dict)
    generated_model_ref: str = ""
    feasibility_report: FeasibilityReport = field(default_factory=FeasibilityReport)
    risk_markers: list[RiskMarker] = field(default_factory=list)
    iteration_history: list[IterationRecord] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "natural_language_input": self.natural_language_input,
            "parsed_spec": self.parsed_spec,
            "generated_model_ref": self.generated_model_ref,
            "feasibility_report": self.feasibility_report.to_dict(),
            "risk_markers": [r.to_dict() for r in self.risk_markers],
            "iteration_history": [i.to_dict() for i in self.iteration_history],
            "clarification_questions": self.clarification_questions,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def confirm(self) -> None:
        if self.status != ProposalStatus.PENDING_REVIEW and self.status != ProposalStatus.ITERATING:
            raise ValueError(f"Cannot confirm proposal in {self.status.value} status")
        self.status = ProposalStatus.CONFIRMED
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="ai.proposal.confirmed",
            aggregate_id=self.id,
            payload={"proposal_id": self.id, "project_id": self.project_id},
        ))

    def reject(self, reason: str = "") -> None:
        self.status = ProposalStatus.REJECTED
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="ai.proposal.rejected",
            aggregate_id=self.id,
            payload={"proposal_id": self.id, "reason": reason},
        ))

    def add_iteration(self, feedback: str, adjusted_params: dict[str, Any]) -> None:
        if self.status not in (ProposalStatus.PENDING_REVIEW, ProposalStatus.ITERATING):
            raise ValueError(f"Cannot iterate proposal in {self.status.value} status")
        self.status = ProposalStatus.ITERATING
        iteration = IterationRecord(
            iteration_id=f"ITER-{len(self.iteration_history) + 1:03d}",
            feedback=feedback,
            adjusted_params=adjusted_params,
        )
        self.iteration_history.append(iteration)
        self.parsed_spec.update(adjusted_params)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)