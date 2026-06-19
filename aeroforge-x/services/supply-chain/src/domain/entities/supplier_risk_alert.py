from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class RiskType(str, Enum):
    DELIVERY_DELAY = "delivery_delay"
    QUALITY_DECLINE = "quality_decline"
    FINANCIAL_RISK = "financial_risk"
    GEOPOLITICAL_RISK = "geopolitical_risk"
    CAPACITY_RISK = "capacity_risk"
    NATURAL_DISASTER = "natural_disaster"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    MITIGATED = "mitigated"
    CLOSED = "closed"


@dataclass
class AffectedItem:
    item_id: str
    item_name: str
    quantity_affected: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_name": self.item_name,
            "quantity_affected": self.quantity_affected,
        }


@dataclass
class MitigationAction:
    action_id: str
    action_type: str
    description: str
    status: str = "pending"
    assigned_to: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "description": self.description,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "completed_at": self.completed_at,
        }


class SupplierRiskAlert(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        network_id: str,
        supplier_id: str,
        risk_type: RiskType,
        risk_level: RiskLevel,
        risk_description: str,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.network_id = network_id
        self.supplier_id = supplier_id
        self.risk_type = risk_type
        self.risk_level = risk_level
        self.risk_description = risk_description
        self.affected_items: list[AffectedItem] = []
        self.mitigation_actions: list[MitigationAction] = []
        self.status = AlertStatus.ACTIVE
        self.detected_at = datetime.now(timezone.utc)
        self.mitigated_at: datetime | None = None

    def add_affected_item(self, item: AffectedItem) -> None:
        self.affected_items.append(item)

    def add_mitigation_action(self, action: MitigationAction) -> None:
        self.mitigation_actions.append(action)

    def mitigate(self) -> None:
        self.status = AlertStatus.MITIGATED
        self.mitigated_at = datetime.now(timezone.utc)

    def close(self) -> None:
        self.status = AlertStatus.CLOSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "network_id": self.network_id,
            "supplier_id": self.supplier_id,
            "risk_type": self.risk_type.value,
            "risk_level": self.risk_level.value,
            "risk_description": self.risk_description,
            "status": self.status.value,
            "detected_at": self.detected_at.isoformat(),
            "mitigated_at": self.mitigated_at.isoformat() if self.mitigated_at else None,
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "affected_items": [i.to_dict() for i in self.affected_items],
            "mitigation_actions": [a.to_dict() for a in self.mitigation_actions],
        })
        return base