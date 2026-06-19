from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class CertificationStandard(str, Enum):
    FAR_23 = "FAR-23"
    FAR_25 = "FAR-25"
    CCAR_23 = "CCAR-23"
    CCAR_25 = "CCAR-25"
    CS_23 = "CS-23"
    CS_25 = "CS-25"


class CertificationAuthority(str, Enum):
    FAA = "FAA"
    EASA = "EASA"
    CAAC = "CAAC"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ComplianceMethod(str, Enum):
    MOC0 = "MOC0"
    MOC1 = "MOC1"
    MOC2 = "MOC2"
    MOC3 = "MOC3"
    MOC4 = "MOC4"
    MOC5 = "MOC5"
    MOC6 = "MOC6"
    MOC7 = "MOC7"
    MOC8 = "MOC8"
    MOC9 = "MOC9"


class ItemStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class EvidenceRef:
    evidence_id: str
    evidence_type: str
    title: str
    reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "title": self.title,
            "reference": self.reference,
        }


@dataclass
class ComplianceItem:
    item_id: str
    plan_id: str
    regulation_clause: str
    clause_title: str
    compliance_method: ComplianceMethod = ComplianceMethod.MOC0
    status: ItemStatus = ItemStatus.NOT_STARTED
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    responsible_person: str = ""
    due_date: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "plan_id": self.plan_id,
            "regulation_clause": self.regulation_clause,
            "clause_title": self.clause_title,
            "compliance_method": self.compliance_method.value,
            "status": self.status.value,
            "evidence_refs": [e.to_dict() for e in self.evidence_refs],
            "responsible_person": self.responsible_person,
            "due_date": self.due_date,
            "notes": self.notes,
        }


@dataclass
class CertificationMilestone:
    milestone_id: str
    name: str
    planned_date: str
    actual_date: str = ""
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestone_id": self.milestone_id,
            "name": self.name,
            "planned_date": self.planned_date,
            "actual_date": self.actual_date,
            "status": self.status,
        }


@dataclass
class ApplicantInfo:
    organization_name: str = ""
    contact_person: str = ""
    contact_email: str = ""
    contact_phone: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_name": self.organization_name,
            "contact_person": self.contact_person,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
        }


class CertificationPlan(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_type: str,
        certification_standard: CertificationStandard,
        certification_authority: CertificationAuthority,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.aircraft_type = aircraft_type
        self.certification_standard = certification_standard
        self.certification_authority = certification_authority
        self.plan_status = PlanStatus.DRAFT
        self.compliance_items: list[ComplianceItem] = []
        self.milestones: list[CertificationMilestone] = []
        self.applicant_info = ApplicantInfo()
        self.submitted_at: datetime | None = None
        self.approved_at: datetime | None = None
        self.created_at = datetime.now(timezone.utc)

    def add_compliance_item(self, item: ComplianceItem) -> None:
        self.compliance_items.append(item)

    def update_compliance_item(
        self,
        item_id: str,
        compliance_method: ComplianceMethod | None = None,
        status: ItemStatus | None = None,
        responsible_person: str | None = None,
        due_date: str | None = None,
    ) -> bool:
        for item in self.compliance_items:
            if item.item_id == item_id:
                if compliance_method is not None:
                    item.compliance_method = compliance_method
                if status is not None:
                    item.status = status
                if responsible_person is not None:
                    item.responsible_person = responsible_person
                if due_date is not None:
                    item.due_date = due_date
                return True
        return False

    def add_evidence_to_item(self, item_id: str, evidence: EvidenceRef) -> bool:
        for item in self.compliance_items:
            if item.item_id == item_id:
                item.evidence_refs.append(evidence)
                return True
        return False

    def add_milestone(self, milestone: CertificationMilestone) -> None:
        self.milestones.append(milestone)

    def set_applicant_info(self, info: ApplicantInfo) -> None:
        self.applicant_info = info

    def submit(self) -> None:
        self.plan_status = PlanStatus.SUBMITTED
        self.submitted_at = datetime.now(timezone.utc)

    def approve(self) -> None:
        self.plan_status = PlanStatus.APPROVED
        self.approved_at = datetime.now(timezone.utc)

    def reject(self) -> None:
        self.plan_status = PlanStatus.REJECTED

    def get_compliance_progress(self) -> dict[str, Any]:
        total = len(self.compliance_items)
        if total == 0:
            return {"total": 0, "completion_rate": 0.0, "by_status": {}}

        by_status: dict[str, int] = {}
        for item in self.compliance_items:
            by_status[item.status.value] = by_status.get(item.status.value, 0) + 1

        completed = by_status.get("compliant", 0) + by_status.get("not_applicable", 0)
        completion_rate = completed / total

        overdue = [
            item for item in self.compliance_items
            if item.due_date and item.status not in (ItemStatus.COMPLIANT, ItemStatus.NOT_APPLICABLE)
            and item.due_date < datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ]

        return {
            "total": total,
            "completion_rate": round(completion_rate, 4),
            "by_status": by_status,
            "overdue_count": len(overdue),
            "overdue_items": [item.regulation_clause for item in overdue],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "aircraft_type": self.aircraft_type,
            "certification_standard": self.certification_standard.value,
            "certification_authority": self.certification_authority.value,
            "plan_status": self.plan_status.value,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat(),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "compliance_items": [i.to_dict() for i in self.compliance_items],
            "milestones": [m.to_dict() for m in self.milestones],
            "applicant_info": self.applicant_info.to_dict(),
            "compliance_progress": self.get_compliance_progress(),
        })
        return base