from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any

from ..value_objects.propagation_action import PropagationAction


@dataclass
class ConfigChange:
    change_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    change_type: str = ""
    title: str = ""
    description: str = ""
    affected_items: list[dict] = field(default_factory=list)
    propagation_map: dict[str, Any] = field(default_factory=dict)
    status: str = "proposed"
    priority: str = "medium"
    impact_level: str = "minor"
    approver_id: str | None = None
    approved_at: datetime | None = None
    implemented_at: datetime | None = None
    requested_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _propagations: list[dict] = field(default_factory=list, repr=False)

    def submit(self) -> None:
        if self.status != "proposed":
            raise ValueError(f"Cannot submit change in {self.status} status")
        self.status = "under_review"
        self.updated_at = datetime.now(timezone.utc)

    def approve(self, approver_id: str) -> None:
        if self.status != "under_review":
            raise ValueError(f"Cannot approve change in {self.status} status")
        self.status = "approved"
        self.approver_id = approver_id
        self.approved_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def reject(self) -> None:
        if self.status not in ("proposed", "under_review"):
            raise ValueError(f"Cannot reject change in {self.status} status")
        self.status = "rejected"
        self.updated_at = datetime.now(timezone.utc)

    def implement(self) -> None:
        if self.status != "approved":
            raise ValueError(f"Cannot implement change in {self.status} status")
        self.status = "implementing"
        self.updated_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        if self.status != "implementing":
            raise ValueError(f"Cannot complete change in {self.status} status")
        self.status = "completed"
        self.implemented_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def add_propagation(self, source_item_id: str, target_item_id: str, action: str) -> None:
        self._propagations.append({
            "source_item_id": source_item_id,
            "target_item_id": target_item_id,
            "action": action,
            "status": "pending",
        })

    def get_propagations(self) -> list[dict]:
        return list(self._propagations)

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "impact_level": self.impact_level,
            "affected_items": self.affected_items,
            "propagation_count": len(self._propagations),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "implemented_at": self.implemented_at.isoformat() if self.implemented_at else None,
        }