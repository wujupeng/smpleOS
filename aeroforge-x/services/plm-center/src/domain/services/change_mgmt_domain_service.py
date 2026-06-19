from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent
from aeroforge_common.utils.helpers import generate_code

logger = logging.getLogger(__name__)


class ECRStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ECOStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ApprovalLevel(str, Enum):
    STANDARD = "standard"
    ELEVATED = "elevated"
    AIRWORTHINESS = "airworthiness"


@dataclass
class ChangeItem:
    object_id: str
    object_type: str
    object_name: str
    current_version: str
    proposed_change: str
    change_type: str = "modify"

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "object_name": self.object_name,
            "current_version": self.current_version,
            "proposed_change": self.proposed_change,
            "change_type": self.change_type,
        }


class ECR(AggregateRoot):
    def __init__(
        self,
        title: str,
        description: str = "",
        submitter: str = "",
    ) -> None:
        super().__init__()
        self.ecr_code: str = generate_code("AAF-ECR")
        self.title = title
        self.description = description
        self.submitter = submitter
        self.status: ECRStatus = ECRStatus.SUBMITTED
        self.approval_level: ApprovalLevel = ApprovalLevel.STANDARD
        self.change_items: list[ChangeItem] = []
        self.impact_analysis: dict[str, Any] = {}
        self.approved_by: str = ""
        self.rejected_reason: str = ""
        self.submitted_at: datetime = datetime.now(timezone.utc)
        self.approval_deadline: datetime | None = None
        self.reviewed_at: datetime | None = None

    def add_change_item(self, item: ChangeItem) -> None:
        self.change_items.append(item)

    def set_impact_analysis(self, analysis: dict[str, Any]) -> None:
        self.impact_analysis = analysis
        if analysis.get("safety_critical"):
            self.approval_level = ApprovalLevel.AIRWORTHINESS
        elif analysis.get("elevated_review"):
            self.approval_level = ApprovalLevel.ELEVATED

    def start_review(self) -> None:
        if self.status != ECRStatus.SUBMITTED:
            raise ValueError(f"Cannot start review from status {self.status.value}")
        self.status = ECRStatus.UNDER_REVIEW
        self.reviewed_at = datetime.now(timezone.utc)
        from datetime import timedelta
        self.approval_deadline = datetime.now(timezone.utc) + timedelta(days=5)

    def approve(self, approved_by: str = "") -> None:
        if self.status != ECRStatus.UNDER_REVIEW:
            raise ValueError(f"Cannot approve from status {self.status.value}")
        self.status = ECRStatus.APPROVED
        self.approved_by = approved_by
        self.add_domain_event(DomainEvent(
            event_type="ecr.approved",
            aggregate_id=self.id,
            payload={
                "ecr_id": self.id,
                "ecr_code": self.ecr_code,
                "approved_by": approved_by,
                "approval_level": self.approval_level.value,
            },
        ))

    def reject(self, reason: str = "") -> None:
        if self.status not in (ECRStatus.SUBMITTED, ECRStatus.UNDER_REVIEW):
            raise ValueError(f"Cannot reject from status {self.status.value}")
        self.status = ECRStatus.REJECTED
        self.rejected_reason = reason

    def withdraw(self) -> None:
        if self.status not in (ECRStatus.SUBMITTED, ECRStatus.UNDER_REVIEW):
            raise ValueError(f"Cannot withdraw from status {self.status.value}")
        self.status = ECRStatus.WITHDRAWN

    def check_approval_timeout(self) -> bool:
        if self.status != ECRStatus.UNDER_REVIEW:
            return False
        if self.approval_deadline and datetime.now(timezone.utc) > self.approval_deadline:
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ecr_code": self.ecr_code,
            "title": self.title,
            "description": self.description,
            "submitter": self.submitter,
            "status": self.status.value,
            "approval_level": self.approval_level.value,
            "change_items": [i.to_dict() for i in self.change_items],
            "impact_analysis": self.impact_analysis,
            "approved_by": self.approved_by,
            "rejected_reason": self.rejected_reason,
            "submitted_at": self.submitted_at.isoformat(),
            "approval_deadline": self.approval_deadline.isoformat() if self.approval_deadline else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


class ECO(AggregateRoot):
    def __init__(
        self,
        ecr_id: str,
        assignee: str = "",
    ) -> None:
        super().__init__()
        self.eco_code: str = generate_code("AAF-ECO")
        self.ecr_id = ecr_id
        self.assignee = assignee
        self.status: ECOStatus = ECOStatus.PENDING
        self.change_items: list[ChangeItem] = []
        self.completed_items: list[str] = []
        self.created_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    def add_change_item(self, item: ChangeItem) -> None:
        self.change_items.append(item)

    def start_execution(self) -> None:
        if self.status != ECOStatus.PENDING:
            raise ValueError(f"Cannot start from status {self.status.value}")
        self.status = ECOStatus.IN_PROGRESS

    def complete_item(self, object_id: str) -> None:
        if object_id not in self.completed_items:
            self.completed_items.append(object_id)

        if len(self.completed_items) >= len(self.change_items):
            self.status = ECOStatus.COMPLETED
            self.completed_at = datetime.now(timezone.utc)
            self.add_domain_event(DomainEvent(
                event_type="eco.completed",
                aggregate_id=self.id,
                payload={
                    "eco_id": self.id,
                    "eco_code": self.eco_code,
                    "ecr_id": self.ecr_id,
                    "items_completed": len(self.completed_items),
                },
            ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "eco_code": self.eco_code,
            "ecr_id": self.ecr_id,
            "assignee": self.assignee,
            "status": self.status.value,
            "change_items": [i.to_dict() for i in self.change_items],
            "completed_items": self.completed_items,
            "progress": f"{len(self.completed_items)}/{len(self.change_items)}",
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ECN(AggregateRoot):
    def __init__(
        self,
        eco_id: str,
        title: str = "",
        description: str = "",
    ) -> None:
        super().__init__()
        self.ecn_code: str = generate_code("AAF-ECN")
        self.eco_id = eco_id
        self.title = title
        self.description = description
        self.affected_parties: list[str] = []
        self.change_summary: list[dict[str, Any]] = []
        self.created_at: datetime = datetime.now(timezone.utc)

    def add_affected_party(self, party: str) -> None:
        if party not in self.affected_parties:
            self.affected_parties.append(party)

    def set_change_summary(self, summary: list[dict[str, Any]]) -> None:
        self.change_summary = summary

    def publish(self) -> None:
        self.add_domain_event(DomainEvent(
            event_type="ecn.published",
            aggregate_id=self.id,
            payload={
                "ecn_id": self.id,
                "ecn_code": self.ecn_code,
                "eco_id": self.eco_id,
                "affected_parties": self.affected_parties,
            },
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ecn_code": self.ecn_code,
            "eco_id": self.eco_id,
            "title": self.title,
            "description": self.description,
            "affected_parties": self.affected_parties,
            "change_summary": self.change_summary,
            "created_at": self.created_at.isoformat(),
        }


class ChangeMgmtDomainService:
    def __init__(self) -> None:
        self._ecrs: dict[str, ECR] = {}
        self._ecos: dict[str, ECO] = {}
        self._ecns: dict[str, ECN] = {}

    def submit_ecr(
        self,
        title: str,
        description: str = "",
        submitter: str = "",
        change_items: list[dict[str, Any]] | None = None,
    ) -> ECR:
        ecr = ECR(title=title, description=description, submitter=submitter)

        if change_items:
            for item_data in change_items:
                item = ChangeItem(
                    object_id=item_data["object_id"],
                    object_type=item_data.get("object_type", "design_object"),
                    object_name=item_data.get("object_name", ""),
                    current_version=item_data.get("current_version", "1.0"),
                    proposed_change=item_data.get("proposed_change", ""),
                    change_type=item_data.get("change_type", "modify"),
                )
                ecr.add_change_item(item)

        self._ecrs[ecr.id] = ecr
        logger.info("ECR submitted: %s by %s", ecr.ecr_code, submitter)
        return ecr

    def approve_ecr(self, ecr_id: str, approved_by: str = "") -> ECR | None:
        ecr = self._ecrs.get(ecr_id)
        if ecr is None:
            return None
        ecr.start_review()
        ecr.approve(approved_by)
        return ecr

    def reject_ecr(self, ecr_id: str, reason: str = "") -> ECR | None:
        ecr = self._ecrs.get(ecr_id)
        if ecr is None:
            return None
        ecr.reject(reason)
        return ecr

    def withdraw_ecr(self, ecr_id: str) -> ECR | None:
        ecr = self._ecrs.get(ecr_id)
        if ecr is None:
            return None
        ecr.withdraw()
        return ecr

    def create_eco(
        self,
        ecr_id: str,
        assignee: str = "",
    ) -> ECO | None:
        ecr = self._ecrs.get(ecr_id)
        if ecr is None or ecr.status != ECRStatus.APPROVED:
            return None

        eco = ECO(ecr_id=ecr_id, assignee=assignee)
        for item in ecr.change_items:
            eco.add_change_item(item)

        self._ecos[eco.id] = eco
        logger.info("ECO created: %s from ECR %s", eco.eco_code, ecr.ecr_code)
        return eco

    def execute_change(self, eco_id: str, object_id: str) -> ECO | None:
        eco = self._ecos.get(eco_id)
        if eco is None:
            return None
        if eco.status == ECOStatus.PENDING:
            eco.start_execution()
        eco.complete_item(object_id)
        return eco

    def generate_ecn(
        self,
        eco_id: str,
        title: str = "",
        description: str = "",
    ) -> ECN | None:
        eco = self._ecos.get(eco_id)
        if eco is None or eco.status != ECOStatus.COMPLETED:
            return None

        ecn = ECN(eco_id=eco_id, title=title, description=description)
        summary = [item.to_dict() for item in eco.change_items]
        ecn.set_change_summary(summary)

        affected = set()
        for item in eco.change_items:
            affected.add(item.object_type)
        for party in affected:
            ecn.add_affected_party(party)

        ecn.publish()
        self._ecns[ecn.id] = ecn
        logger.info("ECN generated: %s from ECO %s", ecn.ecn_code, eco.eco_code)
        return ecn

    def check_approval_timeout(self) -> list[dict[str, Any]]:
        timed_out = []
        for ecr in self._ecrs.values():
            if ecr.check_approval_timeout():
                timed_out.append({
                    "ecr_id": ecr.id,
                    "ecr_code": ecr.ecr_code,
                    "title": ecr.title,
                    "approval_level": ecr.approval_level.value,
                    "action": "send_reminder",
                })
        return timed_out

    def get_ecr(self, ecr_id: str) -> ECR | None:
        return self._ecrs.get(ecr_id)

    def get_eco(self, eco_id: str) -> ECO | None:
        return self._ecos.get(eco_id)

    def get_ecn(self, ecn_id: str) -> ECN | None:
        return self._ecns.get(ecn_id)

    def list_ecrs(self) -> list[ECR]:
        return list(self._ecrs.values())

    def list_ecos(self) -> list[ECO]:
        return list(self._ecos.values())

    def list_ecns(self) -> list[ECN]:
        return list(self._ecns.values())