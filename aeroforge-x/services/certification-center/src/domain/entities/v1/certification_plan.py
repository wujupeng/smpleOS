from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class PlanStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class CertificationPlan:
    def __init__(self, project_id: str, aircraft_type: str, plan_id: str | None = None):
        self.plan_id: str = plan_id or str(uuid4())
        self.project_id: str = project_id
        self.aircraft_type: str = aircraft_type
        self.certification_standard: str = "FAR-25"
        self.certification_authority: str = "FAA"
        self.compliance_items: list[dict[str, Any]] = []
        self.milestones: list[dict[str, Any]] = []
        self.status: PlanStatus = PlanStatus.DRAFT
        self.created_by: str = ""
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def add_compliance_item(self, item: dict[str, Any]) -> None:
        self.compliance_items.append(item)
        self.updated_at = datetime.now(timezone.utc)

    def set_status(self, status: PlanStatus) -> None:
        self.status = status
        self.updated_at = datetime.now(timezone.utc)

    def get_progress(self) -> dict[str, Any]:
        total = len(self.compliance_items)
        if total == 0:
            return {"total": 0, "compliant": 0, "open": 0, "progress_percentage": 0.0}
        compliant = sum(1 for i in self.compliance_items if i.get("status") == "compliant")
        open_items = sum(1 for i in self.compliance_items if i.get("status") == "open")
        return {
            "total": total,
            "compliant": compliant,
            "open": open_items,
            "progress_percentage": round(compliant / total * 100, 1),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "aircraft_type": self.aircraft_type,
            "certification_standard": self.certification_standard,
            "certification_authority": self.certification_authority,
            "compliance_items": self.compliance_items,
            "milestones": self.milestones,
            "status": self.status.value,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }