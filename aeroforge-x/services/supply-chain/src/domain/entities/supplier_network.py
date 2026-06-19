from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class CollaborationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    AT_RISK = "at_risk"


class SupplierTier(str, Enum):
    TIER1 = "Tier1"
    TIER2 = "Tier2"
    TIER3 = "Tier3"


@dataclass
class SuppliedItem:
    item_id: str
    item_name: str
    quantity: float = 0.0
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_name": self.item_name,
            "quantity": self.quantity,
            "unit": self.unit,
        }


@dataclass
class CapacityInfo:
    total_capacity: float = 0.0
    used_capacity: float = 0.0
    available_capacity: float = 0.0
    unit: str = "units/month"

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_capacity": self.total_capacity,
            "used_capacity": self.used_capacity,
            "available_capacity": self.available_capacity,
            "unit": self.unit,
        }


@dataclass
class RiskFactor:
    factor_type: str
    description: str
    severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_type": self.factor_type,
            "description": self.description,
            "severity": self.severity,
        }


@dataclass
class SupplierNetworkNode:
    node_id: str
    supplier_id: str
    supplier_name: str
    tier: SupplierTier
    supplied_items: list[SuppliedItem] = field(default_factory=list)
    capacity: CapacityInfo = field(default_factory=CapacityInfo)
    lead_time_days: float = 0.0
    quality_rating: float = 0.0
    risk_factors: list[RiskFactor] = field(default_factory=list)
    collaboration_status: CollaborationStatus = CollaborationStatus.ACTIVE

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "tier": self.tier.value,
            "supplied_items": [i.to_dict() for i in self.supplied_items],
            "capacity": self.capacity.to_dict(),
            "lead_time_days": self.lead_time_days,
            "quality_rating": self.quality_rating,
            "risk_factors": [r.to_dict() for r in self.risk_factors],
            "collaboration_status": self.collaboration_status.value,
        }


@dataclass
class SupplyEdge:
    from_node_id: str
    to_node_id: str
    material_type: str = ""
    volume: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "material_type": self.material_type,
            "volume": self.volume,
        }


class SupplierNetwork(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        project_id: str,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.nodes: list[SupplierNetworkNode] = []
        self.edges: list[SupplyEdge] = []
        self.risk_score: float = 0.0
        self.created_at = datetime.now(timezone.utc)

    def add_node(self, node: SupplierNetworkNode) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: SupplyEdge) -> None:
        self.edges.append(edge)

    def calculate_risk_score(self) -> float:
        if not self.nodes:
            self.risk_score = 0.0
            return 0.0

        at_risk = sum(1 for n in self.nodes if n.collaboration_status == CollaborationStatus.AT_RISK)
        high_risk_factors = sum(
            1 for n in self.nodes for r in n.risk_factors if r.severity == "high"
        )
        low_quality = sum(1 for n in self.nodes if n.quality_rating < 0.7)

        score = (at_risk * 0.3 + high_risk_factors * 0.2 + low_quality * 0.15) / max(len(self.nodes), 1)
        self.risk_score = round(min(score, 1.0), 4)
        return self.risk_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "risk_score": self.risk_score,
            "nodes_count": len(self.nodes),
            "edges_count": len(self.edges),
            "created_at": self.created_at.isoformat(),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        })
        return base