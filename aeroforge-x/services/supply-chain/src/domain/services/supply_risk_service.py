from __future__ import annotations

import uuid
import random
from datetime import datetime, timezone
from typing import Any

from ..entities.supplier_risk_alert import (
    AffectedItem,
    AlertStatus,
    MitigationAction,
    RiskLevel,
    RiskType,
    SupplierRiskAlert,
)


class SupplyRiskService:
    def __init__(self) -> None:
        self._alerts: dict[str, SupplierRiskAlert] = {}

    def monitor_supply_risks(
        self,
        tenant_id: str,
        network_id: str,
    ) -> list[SupplierRiskAlert]:
        risk_scenarios = [
            (RiskType.DELIVERY_DELAY, "Supplier delivery lead time increasing trend detected"),
            (RiskType.QUALITY_DECLINE, "Supplier quality pass rate declining below threshold"),
            (RiskType.CAPACITY_RISK, "Supplier capacity utilization exceeding 90%"),
            (RiskType.FINANCIAL_RISK, "Supplier financial stability indicators declining"),
            (RiskType.GEOPOLITICAL_RISK, "Geopolitical instability in supplier region"),
        ]

        new_alerts: list[SupplierRiskAlert] = []
        for risk_type, description in risk_scenarios:
            if random.random() < 0.4:
                risk_level = random.choice([RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL])
                supplier_id = f"SUP-{random.randint(1, 8):03d}"

                alert = SupplierRiskAlert(
                    tenant_id=tenant_id,
                    network_id=network_id,
                    supplier_id=supplier_id,
                    risk_type=risk_type,
                    risk_level=risk_level,
                    risk_description=description,
                )

                if random.random() < 0.5:
                    alert.add_affected_item(AffectedItem(
                        item_id=f"item-{random.randint(1, 20)}",
                        item_name=f"material_{random.randint(1, 10)}",
                        quantity_affected=random.uniform(50, 500),
                    ))

                self._alerts[alert.id] = alert
                new_alerts.append(alert)

        return new_alerts

    def assess_risk_impact(
        self,
        alert_id: str,
    ) -> dict[str, Any] | None:
        alert = self._alerts.get(alert_id)
        if not alert:
            return None

        impact_score = {
            RiskLevel.LOW: random.uniform(0.1, 0.3),
            RiskLevel.MEDIUM: random.uniform(0.3, 0.6),
            RiskLevel.HIGH: random.uniform(0.6, 0.8),
            RiskLevel.CRITICAL: random.uniform(0.8, 1.0),
        }.get(alert.risk_level, 0.5)

        return {
            "alert_id": alert_id,
            "risk_type": alert.risk_type.value,
            "risk_level": alert.risk_level.value,
            "impact_score": round(impact_score, 4),
            "affected_items_count": len(alert.affected_items),
            "schedule_impact_days": round(random.uniform(0, 30), 1),
            "delivery_impact_days": round(random.uniform(0, 45), 1),
            "estimated_cost_impact": round(random.uniform(10000, 500000), 2),
        }

    def generate_mitigation_plan(
        self,
        alert_id: str,
    ) -> dict[str, Any] | None:
        alert = self._alerts.get(alert_id)
        if not alert:
            return None

        actions: list[dict[str, Any]] = []

        if alert.risk_type == RiskType.DELIVERY_DELAY:
            actions.append({
                "action_type": "alternative_supplier",
                "description": "Activate backup supplier for affected items",
                "priority": "high",
            })
            actions.append({
                "action_type": "inventory_buffer",
                "description": "Increase safety stock for critical materials",
                "priority": "medium",
            })
        elif alert.risk_type == RiskType.QUALITY_DECLINE:
            actions.append({
                "action_type": "quality_audit",
                "description": "Conduct on-site quality audit at supplier facility",
                "priority": "high",
            })
            actions.append({
                "action_type": "incoming_inspection",
                "description": "Increase incoming inspection frequency",
                "priority": "medium",
            })
        elif alert.risk_type == RiskType.CAPACITY_RISK:
            actions.append({
                "action_type": "capacity_reallocation",
                "description": "Redistribute orders across multiple suppliers",
                "priority": "high",
            })
        else:
            actions.append({
                "action_type": "monitoring",
                "description": "Increase monitoring frequency for this risk",
                "priority": "medium",
            })

        for i, act in enumerate(actions):
            mitigation = MitigationAction(
                action_id=str(uuid.uuid4()),
                action_type=act["action_type"],
                description=act["description"],
            )
            alert.add_mitigation_action(mitigation)

        return {
            "alert_id": alert_id,
            "risk_type": alert.risk_type.value,
            "mitigation_actions": actions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def track_risk_mitigation(
        self,
        alert_id: str,
    ) -> dict[str, Any] | None:
        alert = self._alerts.get(alert_id)
        if not alert:
            return None

        completed = sum(1 for a in alert.mitigation_actions if a.status == "completed")
        total = len(alert.mitigation_actions)

        return {
            "alert_id": alert_id,
            "status": alert.status.value,
            "mitigation_progress": round(completed / max(total, 1), 4),
            "actions_total": total,
            "actions_completed": completed,
            "actions_pending": total - completed,
        }

    def mitigate_alert(self, alert_id: str) -> SupplierRiskAlert | None:
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        alert.mitigate()
        return alert

    def get_alert(self, alert_id: str) -> SupplierRiskAlert | None:
        return self._alerts.get(alert_id)

    def get_active_alerts(self, network_id: str | None = None) -> list[SupplierRiskAlert]:
        alerts = list(self._alerts.values())
        if network_id:
            alerts = [a for a in alerts if a.network_id == network_id]
        return [a for a in alerts if a.status == AlertStatus.ACTIVE]