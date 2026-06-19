from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any


@dataclass
class DesignObject:
    object_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    object_number: str = ""
    object_type: str = ""
    object_name: str = ""
    current_version: int = 1
    status: str = "draft"
    owner_id: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _versions: list[dict] = field(default_factory=list, repr=False)

    def create_version(self, change_summary: str = "", author_id: str | None = None) -> dict:
        version = {
            "version_number": self.current_version,
            "change_summary": change_summary,
            "author_id": author_id,
            "properties": dict(self.properties),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._versions.append(version)
        self.current_version += 1
        self.updated_at = datetime.now(timezone.utc)
        return version

    def get_versions(self) -> list[dict]:
        return list(self._versions)

    def to_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "object_number": self.object_number,
            "object_type": self.object_type,
            "object_name": self.object_name,
            "current_version": self.current_version,
            "status": self.status,
            "owner_id": self.owner_id,
            "version_count": len(self._versions),
        }


@dataclass
class DesignBaseline:
    baseline_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    baseline_name: str = ""
    baseline_type: str = "development"
    object_versions: list[dict] = field(default_factory=list)
    status: str = "open"
    frozen_at: datetime | None = None
    frozen_by: str | None = None
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_object_version(self, object_id: str, version: int) -> None:
        if self.status == "frozen":
            raise ValueError("Cannot modify frozen baseline")
        self.object_versions.append({"object_id": object_id, "version": version})

    def freeze(self, frozen_by: str) -> None:
        if self.status == "frozen":
            raise ValueError("Baseline already frozen")
        if not self.object_versions:
            raise ValueError("Cannot freeze empty baseline")
        self.status = "frozen"
        self.frozen_at = datetime.now(timezone.utc)
        self.frozen_by = frozen_by
        self.updated_at = datetime.now(timezone.utc)

    def unfreeze(self) -> None:
        if self.status != "frozen":
            raise ValueError("Baseline is not frozen")
        self.status = "open"
        self.frozen_at = None
        self.frozen_by = None
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "baseline_id": self.baseline_id,
            "baseline_name": self.baseline_name,
            "baseline_type": self.baseline_type,
            "status": self.status,
            "object_count": len(self.object_versions),
            "frozen_at": self.frozen_at.isoformat() if self.frozen_at else None,
            "frozen_by": self.frozen_by,
        }


@dataclass
class EngineeringChangeRequest:
    ecr_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ecr_number: str = ""
    change_type: str = ""
    title: str = ""
    description: str = ""
    impact_analysis: dict = field(default_factory=dict)
    approval_status: str = "draft"
    approver_id: str | None = None
    approved_at: datetime | None = None
    priority: str = "medium"
    safety_critical: bool = False
    requested_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def submit(self) -> None:
        if self.approval_status != "draft":
            raise ValueError(f"Cannot submit ECR in {self.approval_status} status")
        self.approval_status = "submitted"
        self.updated_at = datetime.now(timezone.utc)

    def review(self) -> None:
        if self.approval_status != "submitted":
            raise ValueError(f"Cannot review ECR in {self.approval_status} status")
        self.approval_status = "under_review"
        self.updated_at = datetime.now(timezone.utc)

    def approve(self, approver_id: str) -> None:
        if self.approval_status != "under_review":
            raise ValueError(f"Cannot approve ECR in {self.approval_status} status")
        if self.safety_critical and self.priority not in ("high", "critical"):
            self.priority = "high"
        self.approval_status = "approved"
        self.approver_id = approver_id
        self.approved_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def reject(self) -> None:
        if self.approval_status not in ("submitted", "under_review"):
            raise ValueError(f"Cannot reject ECR in {self.approval_status} status")
        self.approval_status = "rejected"
        self.updated_at = datetime.now(timezone.utc)

    def analyze_impact(self, affected_objects: list[dict]) -> dict:
        self.impact_analysis = {
            "affected_objects": affected_objects,
            "safety_critical": self.safety_critical,
            "priority": self.priority,
            "bom_impact": any(o.get("type") in ("part", "assembly") for o in affected_objects),
            "process_impact": any(o.get("type") == "process" for o in affected_objects),
        }
        self.updated_at = datetime.now(timezone.utc)
        return self.impact_analysis

    def to_dict(self) -> dict:
        return {
            "ecr_id": self.ecr_id,
            "ecr_number": self.ecr_number,
            "change_type": self.change_type,
            "title": self.title,
            "description": self.description,
            "approval_status": self.approval_status,
            "priority": self.priority,
            "safety_critical": self.safety_critical,
            "impact_analysis": self.impact_analysis,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }


@dataclass
class EngineeringChangeOrder:
    eco_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ecr_id: str = ""
    eco_number: str = ""
    implementation_plan: str = ""
    status: str = "planned"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "eco_id": self.eco_id,
            "ecr_id": self.ecr_id,
            "eco_number": self.eco_number,
            "status": self.status,
        }


@dataclass
class EngineeringChangeNotice:
    ecn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    eco_id: str = ""
    ecn_number: str = ""
    description: str = ""
    effective_date: str | None = None
    status: str = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "ecn_id": self.ecn_id,
            "eco_id": self.eco_id,
            "ecn_number": self.ecn_number,
            "status": self.status,
        }