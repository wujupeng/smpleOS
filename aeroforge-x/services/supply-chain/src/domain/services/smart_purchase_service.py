from __future__ import annotations

import uuid
import random
from datetime import datetime, timezone
from typing import Any

from ..entities.purchase_order import PurchaseOrder


class SmartPurchaseService:
    def __init__(self) -> None:
        self._orders: dict[str, PurchaseOrder] = {}

    def generate_smart_purchase_order(
        self,
        tenant_id: str,
        project_id: str,
        material_requirements: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        requirements = material_requirements or [
            {"item_name": "titanium_alloy", "quantity": 500, "unit": "kg"},
            {"item_name": "aluminum_alloy", "quantity": 800, "unit": "kg"},
            {"item_name": "forging_die", "quantity": 2, "unit": "set"},
        ]

        order_lines: list[dict[str, Any]] = []
        total_cost = 0.0

        for req in requirements:
            unit_price = random.uniform(50, 500)
            quantity = req.get("quantity", 100)
            min_order = random.randint(50, 200)
            actual_qty = max(quantity, min_order)

            discount = 0.0
            if actual_qty > 500:
                discount = 0.05
            elif actual_qty > 200:
                discount = 0.03

            line_cost = actual_qty * unit_price * (1 - discount)
            total_cost += line_cost

            supplier_options = [
                {"supplier_id": f"SUP-{random.randint(1, 4):03d}", "lead_time_days": random.randint(7, 30), "price": round(unit_price, 2)},
                {"supplier_id": f"SUP-{random.randint(5, 8):03d}", "lead_time_days": random.randint(14, 45), "price": round(unit_price * 1.1, 2)},
            ]
            supplier_options.sort(key=lambda s: s["price"])

            order_lines.append({
                "item_name": req.get("item_name", ""),
                "quantity": actual_qty,
                "unit": req.get("unit", "kg"),
                "unit_price": round(unit_price, 2),
                "discount": f"{discount * 100:.0f}%",
                "line_total": round(line_cost, 2),
                "recommended_supplier": supplier_options[0],
                "alternative_suppliers": supplier_options[1:],
            })

        return {
            "order_id": f"SPO-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
            "tenant_id": tenant_id,
            "project_id": project_id,
            "order_lines": order_lines,
            "total_cost": round(total_cost, 2),
            "estimated_delivery_days": max(l.get("recommended_supplier", {}).get("lead_time_days", 30) for l in order_lines),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def optimize_purchase_timing(
        self,
        tenant_id: str,
        project_id: str,
    ) -> dict[str, Any]:
        recommendations: list[dict[str, Any]] = []
        for i in range(5):
            recommendations.append({
                "item_name": f"material_{i + 1}",
                "current_stock": random.randint(50, 500),
                "consumption_rate_per_week": round(random.uniform(20, 100), 1),
                "weeks_of_stock": round(random.uniform(2, 12), 1),
                "recommended_order_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "recommended_quantity": random.randint(200, 1000),
                "urgency": random.choice(["low", "medium", "high"]),
            })

        return {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }