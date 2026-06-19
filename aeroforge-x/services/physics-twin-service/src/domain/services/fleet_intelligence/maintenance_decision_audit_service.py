"""AeroForge-X V6.1 MaintenanceDecisionAuditService

Provides audit trail for PHM maintenance decisions: decision logging,
review workflow for low-confidence predictions, and audit trail queries.
REQ-MC-005~007
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DecisionOutcome(str, Enum):
    SCHEDULE_MAINTENANCE = "ScheduleMaintenance"
    DEFER_MAINTENANCE = "DeferMaintenance"
    ESCALATE_REVIEW = "EscalateReview"
    NO_ACTION = "NoAction"


class ReviewStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    ESCALATED = "Escalated"


@dataclass
class DecisionAuditEntry:
    audit_id: str
    prediction_id: str
    component_id: str
    rul_point_estimate: float
    confidence_lower: float
    confidence_upper: float
    data_quality_score: float
    decision_threshold: float
    decision_outcome: DecisionOutcome
    decided_by: str
    decided_at: str = ""
    review_required: bool = False
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewer: str = ""
    review_comments: str = ""
    reviewed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "audit_id": self.audit_id,
            "prediction_id": self.prediction_id,
            "component_id": self.component_id,
            "rul_point_estimate": self.rul_point_estimate,
            "confidence_lower": self.confidence_lower,
            "confidence_upper": self.confidence_upper,
            "data_quality_score": self.data_quality_score,
            "decision_threshold": self.decision_threshold,
            "decision_outcome": self.decision_outcome.value,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
            "review_required": self.review_required,
            "review_status": self.review_status.value,
            "reviewer": self.reviewer,
            "review_comments": self.review_comments,
            "reviewed_at": self.reviewed_at,
        }


@dataclass
class DecisionReviewResult:
    audit_id: str
    review_status: ReviewStatus
    reviewer: str
    review_comments: str
    is_approved: bool

    def to_dict(self) -> dict:
        return {
            "audit_id": self.audit_id,
            "review_status": self.review_status.value,
            "reviewer": self.reviewer,
            "review_comments": self.review_comments,
            "is_approved": self.is_approved,
        }


@dataclass
class DecisionStatistics:
    total_decisions: int = 0
    scheduled_maintenance: int = 0
    deferred_maintenance: int = 0
    escalated_reviews: int = 0
    no_actions: int = 0
    pending_reviews: int = 0
    avg_data_quality_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_decisions": self.total_decisions,
            "scheduled_maintenance": self.scheduled_maintenance,
            "deferred_maintenance": self.deferred_maintenance,
            "escalated_reviews": self.escalated_reviews,
            "no_actions": self.no_actions,
            "pending_reviews": self.pending_reviews,
            "avg_data_quality_score": round(self.avg_data_quality_score, 2),
        }


class MaintenanceDecisionAuditService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._entries: dict[str, DecisionAuditEntry] = {}
        self._component_index: dict[str, list[str]] = {}

    def logDecision(
        self,
        prediction_id: str,
        component_id: str,
        rul_point_estimate: float,
        confidence_lower: float,
        confidence_upper: float,
        data_quality_score: float,
        decision_threshold: float,
        decision_outcome: DecisionOutcome,
        decided_by: str,
        is_low_confidence: bool = False,
    ) -> DecisionAuditEntry:
        audit_id = f"MDA-{uuid.uuid4().hex[:8]}"

        entry = DecisionAuditEntry(
            audit_id=audit_id,
            prediction_id=prediction_id,
            component_id=component_id,
            rul_point_estimate=rul_point_estimate,
            confidence_lower=confidence_lower,
            confidence_upper=confidence_upper,
            data_quality_score=data_quality_score,
            decision_threshold=decision_threshold,
            decision_outcome=decision_outcome,
            decided_by=decided_by,
            review_required=is_low_confidence,
            review_status=ReviewStatus.PENDING if is_low_confidence else ReviewStatus.APPROVED,
        )

        self._entries[audit_id] = entry

        if component_id not in self._component_index:
            self._component_index[component_id] = []
        self._component_index[component_id].append(audit_id)

        return entry

    def reviewDecision(
        self,
        audit_id: str,
        reviewer: str,
        comments: str,
        is_approved: bool,
    ) -> DecisionReviewResult:
        if audit_id not in self._entries:
            raise ValueError(f"Audit entry not found: {audit_id}")

        entry = self._entries[audit_id]

        if not entry.review_required:
            raise ValueError(f"Audit entry does not require review: {audit_id}")

        entry.reviewer = reviewer
        entry.review_comments = comments
        entry.reviewed_at = ""

        if is_approved:
            entry.review_status = ReviewStatus.APPROVED
        else:
            entry.review_status = ReviewStatus.REJECTED
            if entry.decision_outcome == DecisionOutcome.DEFER_MAINTENANCE:
                entry.decision_outcome = DecisionOutcome.ESCALATE_REVIEW
                entry.review_status = ReviewStatus.ESCALATED

        return DecisionReviewResult(
            audit_id=audit_id,
            review_status=entry.review_status,
            reviewer=reviewer,
            review_comments=comments,
            is_approved=is_approved,
        )

    def queryAuditTrail(
        self, component_id: str, limit: int = 100
    ) -> list[DecisionAuditEntry]:
        audit_ids = self._component_index.get(component_id, [])
        entries = [self._entries[aid] for aid in audit_ids if aid in self._entries]
        return entries[-limit:]

    def getPendingReviews(self) -> list[DecisionAuditEntry]:
        return [
            e for e in self._entries.values()
            if e.review_required and e.review_status == ReviewStatus.PENDING
        ]

    def computeStatistics(self) -> DecisionStatistics:
        entries = list(self._entries.values())
        if not entries:
            return DecisionStatistics()

        stats = DecisionStatistics(total_decisions=len(entries))
        dq_scores = []

        for e in entries:
            dq_scores.append(e.data_quality_score)
            if e.decision_outcome == DecisionOutcome.SCHEDULE_MAINTENANCE:
                stats.scheduled_maintenance += 1
            elif e.decision_outcome == DecisionOutcome.DEFER_MAINTENANCE:
                stats.deferred_maintenance += 1
            elif e.decision_outcome == DecisionOutcome.ESCALATE_REVIEW:
                stats.escalated_reviews += 1
            elif e.decision_outcome == DecisionOutcome.NO_ACTION:
                stats.no_actions += 1

            if e.review_required and e.review_status == ReviewStatus.PENDING:
                stats.pending_reviews += 1

        stats.avg_data_quality_score = sum(dq_scores) / len(dq_scores)

        return stats

    def getEntry(self, audit_id: str) -> Optional[DecisionAuditEntry]:
        return self._entries.get(audit_id)