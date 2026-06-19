from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class ReviewStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    FINDINGS_ISSUED = "findings_issued"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONALLY_APPROVED = "conditionally_approved"


class AirworthinessApproval:
    def __init__(self, certification_plan_id: str, approval_type: str, approval_id: str | None = None):
        self.approval_id: str = approval_id or str(uuid4())
        self.certification_plan_id: str = certification_plan_id
        self.approval_type: str = approval_type
        self.review_status: ReviewStatus = ReviewStatus.SUBMITTED
        self.review_findings: list[dict[str, Any]] = []
        self.conditions: list[str] = []
        self.certificate_number: str | None = None
        self.approval_date: str | None = None
        self.expiry_date: str | None = None
        self.submitted_by: str = ""
        self.submitted_at: datetime = datetime.now(timezone.utc)
        self.reviewed_at: datetime | None = None
        self.reviewed_by: str | None = None

    def add_finding(self, finding: dict[str, Any]) -> None:
        self.review_findings.append(finding)
        if self.review_status == ReviewStatus.UNDER_REVIEW:
            self.review_status = ReviewStatus.FINDINGS_ISSUED

    def approve(self, certificate_number: str, conditions: list[str] | None = None, reviewed_by: str = "") -> None:
        self.review_status = ReviewStatus.APPROVED
        self.certificate_number = certificate_number
        self.conditions = conditions or []
        self.approval_date = datetime.now(timezone.utc).isoformat()
        self.reviewed_at = datetime.now(timezone.utc)
        self.reviewed_by = reviewed_by

    def conditionally_approve(self, conditions: list[str], certificate_number: str, reviewed_by: str = "") -> None:
        self.review_status = ReviewStatus.CONDITIONALLY_APPROVED
        self.conditions = conditions
        self.certificate_number = certificate_number
        self.approval_date = datetime.now(timezone.utc).isoformat()
        self.reviewed_at = datetime.now(timezone.utc)
        self.reviewed_by = reviewed_by

    def reject(self, reason: str, reviewed_by: str = "") -> None:
        self.review_status = ReviewStatus.REJECTED
        self.reviewed_at = datetime.now(timezone.utc)
        self.reviewed_by = reviewed_by
        self.conditions = [reason]

    def is_expired(self) -> bool:
        if not self.expiry_date:
            return False
        return datetime.now(timezone.utc).isoformat() > self.expiry_date

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "certification_plan_id": self.certification_plan_id,
            "approval_type": self.approval_type,
            "review_status": self.review_status.value,
            "review_findings": self.review_findings,
            "conditions": self.conditions,
            "certificate_number": self.certificate_number,
            "approval_date": self.approval_date,
            "expiry_date": self.expiry_date,
            "submitted_by": self.submitted_by,
            "submitted_at": self.submitted_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
        }