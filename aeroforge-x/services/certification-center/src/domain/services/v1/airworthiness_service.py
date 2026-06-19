from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from src.domain.entities.v1.airworthiness_approval import AirworthinessApproval, ReviewStatus

logger = logging.getLogger(__name__)


class AirworthinessDirective:
    def __init__(self, ad_number: str, title: str, effective_date: str):
        self.ad_number = ad_number
        self.title = title
        self.effective_date = effective_date
        self.compliance_required_by: str | None = None
        self.applicability: str = ""
        self.description: str = ""
        self.compliance_action: str = ""
        self.status: str = "active"
        self.affected_aircraft: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "ad_number": self.ad_number,
            "title": self.title,
            "effective_date": self.effective_date,
            "compliance_required_by": self.compliance_required_by,
            "applicability": self.applicability,
            "description": self.description,
            "compliance_action": self.compliance_action,
            "status": self.status,
            "affected_aircraft": self.affected_aircraft,
        }


class ServiceBulletin:
    def __init__(self, sb_number: str, title: str, issuer: str, issue_date: str):
        self.sb_number = sb_number
        self.title = title
        self.issuer = issuer
        self.issue_date = issue_date
        self.priority: str = "advisory"
        self.applicability: str = ""
        self.description: str = ""
        self.compliance_action: str = ""
        self.status: str = "active"
        self.affected_aircraft: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "sb_number": self.sb_number,
            "title": self.title,
            "issuer": self.issuer,
            "issue_date": self.issue_date,
            "priority": self.priority,
            "applicability": self.applicability,
            "description": self.description,
            "compliance_action": self.compliance_action,
            "status": self.status,
            "affected_aircraft": self.affected_aircraft,
        }


class AirworthinessService:
    def __init__(self, event_publisher: Any | None = None):
        self._event_publisher = event_publisher
        self._approvals: dict[str, AirworthinessApproval] = {}
        self._directives: dict[str, AirworthinessDirective] = {}
        self._bulletins: dict[str, ServiceBulletin] = {}
        self._continuous_records: dict[str, list[dict[str, Any]]] = {}

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    async def submit_approval_application(self, certification_plan_id: str, approval_type: str, submitted_by: str = "") -> AirworthinessApproval:
        approval = AirworthinessApproval(certification_plan_id, approval_type)
        approval.submitted_by = submitted_by
        self._approvals[approval.approval_id] = approval
        await self._publish_event("cert.approval.submitted", {
            "approval_id": approval.approval_id,
            "plan_id": certification_plan_id,
            "type": approval_type,
        })
        logger.info(f"Approval application submitted: {approval.approval_id}")
        return approval

    def track_review_progress(self, approval_id: str) -> dict[str, Any]:
        approval = self._approvals.get(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        return {
            "approval_id": approval_id,
            "review_status": approval.review_status.value,
            "findings_count": len(approval.review_findings),
            "conditions_count": len(approval.conditions),
            "certificate_number": approval.certificate_number,
        }

    def manage_review_findings(self, approval_id: str, finding: dict[str, Any]) -> AirworthinessApproval:
        approval = self._approvals.get(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        approval.add_finding(finding)
        return approval

    def manage_certificate_lifecycle(self, approval_id: str, action: str, **kwargs: Any) -> dict[str, Any]:
        approval = self._approvals.get(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        if action == "approve":
            approval.approve(kwargs.get("certificate_number", ""), kwargs.get("conditions"), kwargs.get("reviewed_by", ""))
        elif action == "conditionally_approve":
            approval.conditionally_approve(kwargs.get("conditions", []), kwargs.get("certificate_number", ""), kwargs.get("reviewed_by", ""))
        elif action == "reject":
            approval.reject(kwargs.get("reason", ""), kwargs.get("reviewed_by", ""))
        elif action == "renew":
            approval.expiry_date = kwargs.get("new_expiry_date")
        elif action == "revoke":
            approval.review_status = ReviewStatus.REJECTED
            approval.conditions.append("Certificate revoked")

        return {
            "approval_id": approval_id,
            "action": action,
            "new_status": approval.review_status.value,
            "certificate_number": approval.certificate_number,
        }

    def track_ad_compliance(self, aircraft_sn: str) -> dict[str, Any]:
        applicable_ads = [ad for ad in self._directives.values() if aircraft_sn in ad.affected_aircraft or not ad.affected_aircraft]
        records = self._continuous_records.get(aircraft_sn, [])
        ad_records = [r for r in records if r.get("record_type") == "ad_compliance"]
        compliant_ads = set(r.get("ad_number") for r in ad_records if r.get("compliance_status") == "compliant")
        pending_ads = [ad for ad in applicable_ads if ad.ad_number not in compliant_ads]

        return {
            "aircraft_sn": aircraft_sn,
            "total_applicable_ads": len(applicable_ads),
            "compliant_ads": len(compliant_ads),
            "pending_ads": len(pending_ads),
            "pending_ad_details": [ad.to_dict() for ad in pending_ads],
        }

    def track_sb_compliance(self, aircraft_sn: str) -> dict[str, Any]:
        applicable_sbs = [sb for sb in self._bulletins.values() if aircraft_sn in sb.affected_aircraft or not sb.affected_aircraft]
        records = self._continuous_records.get(aircraft_sn, [])
        sb_records = [r for r in records if r.get("record_type") == "sb_compliance"]
        executed_sbs = set(r.get("sb_number") for r in sb_records if r.get("compliance_status") == "compliant")
        pending_sbs = [sb for sb in applicable_sbs if sb.sb_number not in executed_sbs]

        return {
            "aircraft_sn": aircraft_sn,
            "total_applicable_sbs": len(applicable_sbs),
            "executed_sbs": len(executed_sbs),
            "pending_sbs": len(pending_sbs),
        }

    def add_airworthiness_directive(self, ad: AirworthinessDirective) -> None:
        self._directives[ad.ad_number] = ad

    def add_service_bulletin(self, sb: ServiceBulletin) -> None:
        self._bulletins[sb.sb_number] = sb

    def record_continuous_airworthiness(self, aircraft_sn: str, record: dict[str, Any]) -> None:
        self._continuous_records.setdefault(aircraft_sn, []).append(record)

    def get_approval(self, approval_id: str) -> AirworthinessApproval | None:
        return self._approvals.get(approval_id)