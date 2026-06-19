from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class ComplianceStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"


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


class ComplianceItem:
    def __init__(self, plan_id: str, regulation_clause: str, clause_title: str, item_id: str | None = None):
        self.item_id: str = item_id or str(uuid4())
        self.plan_id: str = plan_id
        self.regulation_clause: str = regulation_clause
        self.clause_title: str = clause_title
        self.compliance_method: ComplianceMethod | None = None
        self.status: ComplianceStatus = ComplianceStatus.OPEN
        self.evidence_refs: list[str] = []
        self.responsible_person: str = ""
        self.due_date: str | None = None
        self.evidence_gap: bool = True
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def assign_compliance_method(self, method: ComplianceMethod) -> None:
        self.compliance_method = method
        self.updated_at = datetime.now(timezone.utc)

    def link_evidence(self, evidence_ref: str) -> None:
        if evidence_ref not in self.evidence_refs:
            self.evidence_refs.append(evidence_ref)
        self.evidence_gap = len(self.evidence_refs) == 0
        if self.evidence_refs and self.status == ComplianceStatus.OPEN:
            self.status = ComplianceStatus.IN_PROGRESS
        self.updated_at = datetime.now(timezone.utc)

    def mark_compliant(self) -> None:
        if self.evidence_gap:
            raise ValueError("Cannot mark compliant: evidence gap exists")
        self.status = ComplianceStatus.COMPLIANT
        self.updated_at = datetime.now(timezone.utc)

    def mark_non_compliant(self) -> None:
        self.status = ComplianceStatus.NON_COMPLIANT
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "plan_id": self.plan_id,
            "regulation_clause": self.regulation_clause,
            "clause_title": self.clause_title,
            "compliance_method": self.compliance_method.value if self.compliance_method else None,
            "status": self.status.value,
            "evidence_refs": self.evidence_refs,
            "responsible_person": self.responsible_person,
            "due_date": self.due_date,
            "evidence_gap": self.evidence_gap,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }