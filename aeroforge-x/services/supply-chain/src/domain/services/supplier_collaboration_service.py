from __future__ import annotations

import uuid
import random
from datetime import datetime, timezone
from typing import Any

from ..entities.supplier_network import (
    CapacityInfo,
    CollaborationStatus,
    RiskFactor,
    SupplierNetwork,
    SupplierNetworkNode,
    SupplierTier,
    SuppliedItem,
    SupplyEdge,
)


_SUPPLIER_TEMPLATES = [
    ("SUP-001", "AeroForge Materials Co.", SupplierTier.TIER1, ["titanium_alloy", "aluminum_alloy"]),
    ("SUP-002", "Precision Forging Ltd.", SupplierTier.TIER1, ["forged_billet", "preform"]),
    ("SUP-003", "Heat Treat Inc.", SupplierTier.TIER1, ["heat_treatment_service"]),
    ("SUP-004", "CNC Machining Corp.", SupplierTier.TIER1, ["machined_part"]),
    ("SUP-005", "Raw Metal Suppliers", SupplierTier.TIER2, ["raw_titanium", "raw_aluminum"]),
    ("SUP-006", "Chemical Processing Co.", SupplierTier.TIER2, ["surface_treatment_chemical"]),
    ("SUP-007", "Tool & Die Works", SupplierTier.TIER2, ["forging_die", "cutting_tool"]),
    ("SUP-008", "Ore Mining Corp.", SupplierTier.TIER3, ["titanium_ore", "bauxite"]),
]


class SupplierCollaborationService:
    def __init__(self) -> None:
        self._networks: dict[str, SupplierNetwork] = {}

    def build_supplier_network(
        self,
        tenant_id: str,
        project_id: str,
    ) -> SupplierNetwork:
        network = SupplierNetwork(tenant_id=tenant_id, project_id=project_id)

        for supplier_id, name, tier, items in _SUPPLIER_TEMPLATES:
            supplied = [
                SuppliedItem(item_id=f"item-{supplier_id}-{i}", item_name=item_name)
                for i, item_name in enumerate(items)
            ]
            capacity = CapacityInfo(
                total_capacity=random.uniform(500, 5000),
                used_capacity=random.uniform(200, 4000),
            )
            capacity.available_capacity = capacity.total_capacity - capacity.used_capacity

            node = SupplierNetworkNode(
                node_id=str(uuid.uuid4()),
                supplier_id=supplier_id,
                supplier_name=name,
                tier=tier,
                supplied_items=supplied,
                capacity=capacity,
                lead_time_days=random.uniform(5, 60),
                quality_rating=random.uniform(0.7, 0.99),
            )

            if random.random() < 0.2:
                node.risk_factors.append(RiskFactor(
                    factor_type="capacity_risk",
                    description="Capacity utilization above 85%",
                    severity="medium",
                ))
                node.collaboration_status = CollaborationStatus.AT_RISK

            network.add_node(node)

        tier1_nodes = [n for n in network.nodes if n.tier == SupplierTier.TIER1]
        tier2_nodes = [n for n in network.nodes if n.tier == SupplierTier.TIER2]
        tier3_nodes = [n for n in network.nodes if n.tier == SupplierTier.TIER3]

        for t2 in tier2_nodes:
            for t1 in tier1_nodes[:2]:
                network.add_edge(SupplyEdge(
                    from_node_id=t2.node_id,
                    to_node_id=t1.node_id,
                    material_type=t2.supplied_items[0].item_name if t2.supplied_items else "",
                    volume=random.uniform(100, 1000),
                ))

        for t3 in tier3_nodes:
            for t2 in tier2_nodes[:2]:
                network.add_edge(SupplyEdge(
                    from_node_id=t3.node_id,
                    to_node_id=t2.node_id,
                    material_type=t3.supplied_items[0].item_name if t3.supplied_items else "",
                    volume=random.uniform(500, 5000),
                ))

        network.calculate_risk_score()
        self._networks[network.id] = network
        return network

    def share_demand_forecast(
        self,
        network_id: str,
        forecast_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        network = self._networks.get(network_id)
        if not network:
            return None

        forecast = forecast_data or {
            "period": "2026-Q3",
            "total_demand": random.randint(1000, 5000),
            "items": [
                {"item_name": "forged_billet", "quantity": random.randint(200, 800)},
                {"item_name": "titanium_alloy", "quantity": random.randint(100, 500)},
            ],
        }

        confirmations = []
        for node in network.nodes:
            if node.collaboration_status == CollaborationStatus.ACTIVE:
                confirmations.append({
                    "supplier_id": node.supplier_id,
                    "supplier_name": node.supplier_name,
                    "can_fulfill": random.random() > 0.2,
                    "confirmed_capacity": node.capacity.available_capacity,
                    "confirmed_lead_time": node.lead_time_days,
                })

        return {
            "network_id": network_id,
            "forecast": forecast,
            "supplier_confirmations": confirmations,
            "shared_at": datetime.now(timezone.utc).isoformat(),
        }

    def track_supplier_performance(
        self,
        network_id: str,
        supplier_id: str,
    ) -> dict[str, Any] | None:
        network = self._networks.get(network_id)
        if not network:
            return None

        node = next((n for n in network.nodes if n.supplier_id == supplier_id), None)
        if not node:
            return None

        return {
            "supplier_id": supplier_id,
            "supplier_name": node.supplier_name,
            "tier": node.tier.value,
            "on_time_delivery_rate": round(random.uniform(0.75, 0.99), 4),
            "quality_pass_rate": round(node.quality_rating, 4),
            "avg_response_time_hours": round(random.uniform(2, 48), 1),
            "performance_trend": [round(random.uniform(0.8, 0.98), 4) for _ in range(6)],
            "rating": round(random.uniform(3.5, 5.0), 1),
        }

    def manage_supplier_capacity(
        self,
        network_id: str,
    ) -> dict[str, Any] | None:
        network = self._networks.get(network_id)
        if not network:
            return None

        conflicts = []
        for node in network.nodes:
            utilization = node.capacity.used_capacity / max(node.capacity.total_capacity, 1)
            if utilization > 0.85:
                conflicts.append({
                    "supplier_id": node.supplier_id,
                    "supplier_name": node.supplier_name,
                    "utilization": round(utilization, 4),
                    "available_capacity": node.capacity.available_capacity,
                    "conflict_severity": "high" if utilization > 0.95 else "medium",
                })

        return {
            "network_id": network_id,
            "total_suppliers": len(network.nodes),
            "capacity_conflicts": conflicts,
            "conflict_count": len(conflicts),
        }

    def get_network(self, network_id: str) -> SupplierNetwork | None:
        return self._networks.get(network_id)