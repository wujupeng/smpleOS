from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


@dataclass
class InventoryItem:
    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: str = ""
    item_code: str = ""
    item_name: str = ""
    warehouse_location: str = ""
    quantity_on_hand: int = 0
    quantity_reserved: int = 0
    reorder_point: int = 10
    safety_stock: int = 5
    unit_cost: float = 0.0
    unit: str = "pcs"
    material_type: str = ""
    last_restocked_at: str = ""
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "item_code": self.item_code,
            "item_name": self.item_name,
            "warehouse_location": self.warehouse_location,
            "quantity_on_hand": self.quantity_on_hand,
            "quantity_reserved": self.quantity_reserved,
            "quantity_available": self.quantity_available,
            "reorder_point": self.reorder_point,
            "safety_stock": self.safety_stock,
            "unit_cost": self.unit_cost,
            "unit": self.unit,
            "material_type": self.material_type,
            "last_restocked_at": self.last_restocked_at,
            "is_below_reorder": self.is_below_reorder,
            "is_below_safety": self.is_below_safety,
        }

    @property
    def quantity_available(self) -> int:
        return max(0, self.quantity_on_hand - self.quantity_reserved)

    @property
    def is_below_reorder(self) -> bool:
        return self.quantity_available <= self.reorder_point

    @property
    def is_below_safety(self) -> bool:
        return self.quantity_available <= self.safety_stock

    def receive_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        self.quantity_on_hand += quantity
        self.last_restocked_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="inventory.received",
            aggregate_id=self.id,
            payload={"item_code": self.item_code, "quantity": quantity},
        ))

    def reserve_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if quantity > self.quantity_available:
            raise ValueError(
                f"Cannot reserve {quantity}, only {self.quantity_available} available"
            )
        self.quantity_reserved += quantity

    def release_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        self.quantity_reserved = max(0, self.quantity_reserved - quantity)

    def consume_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if quantity > self.quantity_on_hand:
            raise ValueError(
                f"Cannot consume {quantity}, only {self.quantity_on_hand} on hand"
            )
        self.quantity_on_hand -= quantity
        self.quantity_reserved = max(0, self.quantity_reserved - quantity)

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)