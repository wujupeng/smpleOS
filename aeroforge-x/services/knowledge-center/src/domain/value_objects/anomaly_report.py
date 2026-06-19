from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AnomalyReport:
    anomaly_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    anomaly_type: str = ""
    affected_node_ids: list[str] = field(default_factory=list)
    severity: str = "medium"
    description: str = ""
    remediation: str = ""
    status: str = "open"
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def acknowledge(self) -> None:
        self.status = "acknowledged"

    def resolve(self, resolved_by: str) -> None:
        self.status = "resolved"
        self.resolved_by = resolved_by
        self.resolved_at = datetime.now(timezone.utc)

    def dismiss(self) -> None:
        self.status = "dismissed"

    def to_dict(self) -> dict:
        return {
            "anomaly_id": self.anomaly_id,
            "anomaly_type": self.anomaly_type,
            "affected_node_ids": self.affected_node_ids,
            "severity": self.severity,
            "description": self.description,
            "remediation": self.remediation,
            "status": self.status,
        }