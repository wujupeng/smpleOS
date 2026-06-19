from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class ApprovalType(str, Enum):
    TYPE_CERTIFICATE = "Type_Certificate"
    SUPPLEMENTAL_TYPE_CERTIFICATE = "Supplemental_Type_Certificate"
    PRODUCTION_CERTIFICATE = "Production_Certificate"
    AIRWORTHINESS_CERTIFICATE = "Airworthiness_Certificate"


class ReviewStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ADDITIONAL_INFO_REQUIRED = "additional_info_required"
    APPROVED = "approved"
    REJECTED = "rejected"


class FindingType(str, Enum):
    OBSERVATION = "observation"
    FINDING = "finding"
    MAJOR_FINDING = "major_finding"


class FindingStatus(str, Enum):
    OPEN = "open"
    CORRECTIVE_ACTION_ASSIGNED = "corrective_action_assigned"
    CORRECTIVE_ACTION_IN_PROGRESS = "corrective_action_in_progress"
    VERIFIED = "verified"
    CLOSED = "closed"


@dataclass
class ReviewFinding:
    finding_id: str
    finding_type: FindingType
    description: str
    clause_reference: str = ""
    corrective_action: str = ""
    assigned_to: str = ""
    due_date: str = ""
    status: FindingStatus = FindingStatus.OPEN
    verified_at: datetime | None = None
    verified_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "finding_type": self.finding_type.value,
            "description": self.description,
            "clause_reference": self.clause_reference,
            "corrective_action": self.corrective_action,
            "assigned_to": self.assigned_to,
            "due_date": self.due_date,
            "status": self.status.value,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verified_by": self.verified_by,
        }


@dataclass
class ApprovalCondition:
    condition_id: str
    description: str
    is_satisfied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "description": self.description,
            "is_satisfied": self.is_satisfied,
        }


@dataclass
class ApplicantInformation:
    organization: str = ""
    contact_person: str = ""
    contact_email: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization": self.organization,
            "contact_person": self.contact_person,
            "contact_email": self.contact_email,
        }


class AirworthinessApproval(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        certification_plan_id: str,
        approval_type: ApprovalType,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.certification_plan_id = certification_plan_id
        self.approval_type = approval_type
        self.review_status = ReviewStatus.SUBMITTED
        self.applicant_info = ApplicantInformation()
        self.review_findings: list[ReviewFinding] = []
        self.conditions: list[ApprovalCondition] = []
        self.approval_date: datetime | None = None
        self.expiry_date: datetime | None = None
        self.certificate_number: str = ""
        self.submitted_at = datetime.now(timezone.utc)
        self.created_at = datetime.now(timezone.utc)

    def add_finding(self, finding: ReviewFinding) -> None:
        self.review_findings.append(finding)
        self.review_status = ReviewStatus.UNDER_REVIEW

    def update_finding(
        self,
        finding_id: str,
        corrective_action: str | None = None,
        status: FindingStatus | None = None,
        assigned_to: str | None = None,
    ) -> bool:
        for f in self.review_findings:
            if f.finding_id == finding_id:
                if corrective_action is not None:
                    f.corrective_action = corrective_action
                if status is not None:
                    f.status = status
                if assigned_to is not None:
                    f.assigned_to = assigned_to
                return True
        return False

    def verify_finding(self, finding_id: str, verified_by: str) -> bool:
        for f in self.review_findings:
            if f.finding_id == finding_id:
                f.status = FindingStatus.VERIFIED
                f.verified_at = datetime.now(timezone.utc)
                f.verified_by = verified_by
                return True
        return False

    def close_finding(self, finding_id: str) -> bool:
        for f in self.review_findings:
            if f.finding_id == finding_id and f.status == FindingStatus.VERIFIED:
                f.status = FindingStatus.CLOSED
                return True
        return False

    def add_condition(self, condition: ApprovalCondition) -> None:
        self.conditions.append(condition)

    def satisfy_condition(self, condition_id: str) -> bool:
        for c in self.conditions:
            if c.condition_id == condition_id:
                c.is_satisfied = True
                return True
        return False

    def request_additional_info(self) -> None:
        self.review_status = ReviewStatus.ADDITIONAL_INFO_REQUIRED

    def all_findings_closed(self) -> bool:
        return all(f.status == FindingStatus.CLOSED for f in self.review_findings)

    def all_conditions_satisfied(self) -> bool:
        return all(c.is_satisfied for c in self.conditions)

    def issue_certificate(self, certificate_number: str) -> bool:
        if not self.all_findings_closed():
            return False
        if not self.all_conditions_satisfied():
            return False

        self.review_status = ReviewStatus.APPROVED
        self.certificate_number = certificate_number
        self.approval_date = datetime.now(timezone.utc)
        self.expiry_date = datetime(
            self.approval_date.year + 5,
            self.approval_date.month,
            self.approval_date.day,
            tzinfo=timezone.utc,
        )
        return True

    def reject_approval(self) -> None:
        self.review_status = ReviewStatus.REJECTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "certification_plan_id": self.certification_plan_id,
            "approval_type": self.approval_type.value,
            "review_status": self.review_status.value,
            "certificate_number": self.certificate_number,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "submitted_at": self.submitted_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "applicant_info": self.applicant_info.to_dict(),
            "review_findings": [f.to_dict() for f in self.review_findings],
            "conditions": [c.to_dict() for c in self.conditions],
            "all_findings_closed": self.all_findings_closed(),
            "all_conditions_satisfied": self.all_conditions_satisfied(),
        })
        return base