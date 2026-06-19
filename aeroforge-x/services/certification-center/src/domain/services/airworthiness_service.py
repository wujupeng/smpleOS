from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ..entities.airworthiness_approval import (
    AirworthinessApproval,
    ApprovalCondition,
    ApprovalType,
    ApplicantInformation,
    FindingStatus,
    FindingType,
    ReviewFinding,
    ReviewStatus,
)


class AirworthinessService:
    def __init__(self) -> None:
        self._approvals: dict[str, AirworthinessApproval] = {}

    def submit_approval_application(
        self,
        tenant_id: str,
        certification_plan_id: str,
        approval_type: ApprovalType,
        applicant_info: ApplicantInformation | None = None,
    ) -> AirworthinessApproval:
        approval = AirworthinessApproval(
            tenant_id=tenant_id,
            certification_plan_id=certification_plan_id,
            approval_type=approval_type,
        )
        if applicant_info:
            approval.applicant_info = applicant_info

        self._approvals[approval.id] = approval
        return approval

    def track_review_progress(self, approval_id: str) -> dict[str, Any] | None:
        approval = self._approvals.get(approval_id)
        if not approval:
            return None

        findings_summary = {
            "total": len(approval.review_findings),
            "open": sum(1 for f in approval.review_findings if f.status == FindingStatus.OPEN),
            "in_progress": sum(1 for f in approval.review_findings if f.status in (FindingStatus.CORRECTIVE_ACTION_ASSIGNED, FindingStatus.CORRECTIVE_ACTION_IN_PROGRESS)),
            "verified": sum(1 for f in approval.review_findings if f.status == FindingStatus.VERIFIED),
            "closed": sum(1 for f in approval.review_findings if f.status == FindingStatus.CLOSED),
        }

        return {
            "approval_id": approval.id,
            "review_status": approval.review_status.value,
            "findings_summary": findings_summary,
            "conditions_met": sum(1 for c in approval.conditions if c.is_satisfied),
            "conditions_total": len(approval.conditions),
            "all_findings_closed": approval.all_findings_closed(),
            "all_conditions_satisfied": approval.all_conditions_satisfied(),
        }

    def manage_review_findings(
        self,
        approval_id: str,
        finding_type: FindingType,
        description: str,
        clause_reference: str = "",
        corrective_action: str = "",
        assigned_to: str = "",
    ) -> AirworthinessApproval | None:
        approval = self._approvals.get(approval_id)
        if not approval:
            return None

        finding = ReviewFinding(
            finding_id=str(uuid.uuid4()),
            finding_type=finding_type,
            description=description,
            clause_reference=clause_reference,
            corrective_action=corrective_action,
            assigned_to=assigned_to,
        )
        approval.add_finding(finding)
        return approval

    def update_finding(
        self,
        approval_id: str,
        finding_id: str,
        corrective_action: str | None = None,
        status: FindingStatus | None = None,
        assigned_to: str | None = None,
    ) -> AirworthinessApproval | None:
        approval = self._approvals.get(approval_id)
        if not approval:
            return None
        approval.update_finding(finding_id, corrective_action, status, assigned_to)
        return approval

    def verify_finding(
        self,
        approval_id: str,
        finding_id: str,
        verified_by: str,
    ) -> AirworthinessApproval | None:
        approval = self._approvals.get(approval_id)
        if not approval:
            return None
        approval.verify_finding(finding_id, verified_by)
        return approval

    def close_finding(
        self,
        approval_id: str,
        finding_id: str,
    ) -> AirworthinessApproval | None:
        approval = self._approvals.get(approval_id)
        if not approval:
            return None
        approval.close_finding(finding_id)
        return approval

    def issue_certificate(
        self,
        approval_id: str,
        certificate_number: str | None = None,
    ) -> AirworthinessApproval | None:
        approval = self._approvals.get(approval_id)
        if not approval:
            return None

        if not certificate_number:
            cert_prefix = {
                ApprovalType.TYPE_CERTIFICATE: "TC",
                ApprovalType.SUPPLEMENTAL_TYPE_CERTIFICATE: "STC",
                ApprovalType.PRODUCTION_CERTIFICATE: "PC",
                ApprovalType.AIRWORTHINESS_CERTIFICATE: "AC",
            }
            prefix = cert_prefix.get(approval.approval_type, "CERT")
            certificate_number = f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        success = approval.issue_certificate(certificate_number)
        if not success:
            return None
        return approval

    def manage_certificate_lifecycle(
        self, approval_id: str
    ) -> dict[str, Any] | None:
        approval = self._approvals.get(approval_id)
        if not approval:
            return None

        now = datetime.now(timezone.utc)
        is_expired = approval.expiry_date and approval.expiry_date < now
        days_to_expiry = (approval.expiry_date - now).days if approval.expiry_date and not is_expired else 0

        return {
            "certificate_number": approval.certificate_number,
            "approval_type": approval.approval_type.value,
            "approval_date": approval.approval_date.isoformat() if approval.approval_date else None,
            "expiry_date": approval.expiry_date.isoformat() if approval.expiry_date else None,
            "is_expired": is_expired,
            "days_to_expiry": days_to_expiry,
            "needs_renewal": days_to_expiry < 180 and not is_expired,
        }

    def get_approval(self, approval_id: str) -> AirworthinessApproval | None:
        return self._approvals.get(approval_id)