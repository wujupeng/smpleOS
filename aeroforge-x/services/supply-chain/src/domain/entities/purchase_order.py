from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class OrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    CLOSED = "closed"


@dataclass
class OrderItem:
    material_code: str = ""
    material_name: str = ""
    quantity: int = 1
    unit_price: float = 0.0
    unit: str = "pcs"
    delivery_date: str = ""
    received_quantity: int = 0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_code": self.material_code,
            "material_name": self.material_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "unit": self.unit,
            "delivery_date": self.delivery_date,
            "received_quantity": self.received_quantity,
            "notes": self.notes,
        }

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class PurchaseOrder:
    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: str = ""
    order_code: str = ""
    supplier_id: str = ""
    supplier_name: str = ""
    status: OrderStatus = OrderStatus.DRAFT
    order_items: list[OrderItem] = field(default_factory=list)
    total_amount: float = 0.0
    currency: str = "CNY"
    payment_terms: str = "net30"
    expected_delivery_date: str = ""
    actual_delivery_date: str = ""
    iqc_required: bool = True
    iqc_status: str = ""
    notes: str = ""
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "order_code": self.order_code,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "status": self.status.value,
            "order_items": [item.to_dict() for item in self.order_items],
            "total_amount": self.total_amount,
            "currency": self.currency,
            "payment_terms": self.payment_terms,
            "expected_delivery_date": self.expected_delivery_date,
            "actual_delivery_date": self.actual_delivery_date,
            "iqc_required": self.iqc_required,
            "iqc_status": self.iqc_status,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def compute_total(self) -> float:
        self.total_amount = round(sum(item.subtotal for item in self.order_items), 2)
        return self.total_amount

    def submit(self) -> None:
        if self.status != OrderStatus.DRAFT:
            raise ValueError(f"Cannot submit order in {self.status.value} status")
        self.status = OrderStatus.SUBMITTED
        self.add_domain_event(DomainEvent(
            event_type="purchase_order.submitted",
            aggregate_id=self.id,
            payload={"order_id": self.id, "order_code": self.order_code},
        ))

    def confirm(self) -> None:
        if self.status != OrderStatus.SUBMITTED:
            raise ValueError(f"Cannot confirm order in {self.status.value} status")
        self.status = OrderStatus.CONFIRMED

    def ship(self) -> None:
        if self.status != OrderStatus.CONFIRMED:
            raise ValueError(f"Cannot ship order in {self.status.value} status")
        self.status = OrderStatus.IN_TRANSIT

    def receive(self, received_items: list[dict[str, int]] | None = None) -> None:
        if self.status != OrderStatus.IN_TRANSIT:
            raise ValueError(f"Cannot receive order in {self.status.value} status")
        self.status = OrderStatus.RECEIVED
        self.actual_delivery_date = datetime.now(timezone.utc).isoformat()

        if received_items:
            for recv in received_items:
                for item in self.order_items:
                    if item.material_code == recv.get("material_code"):
                        item.received_quantity = recv.get("quantity", item.received_quantity)

        if self.iqc_required:
            self.iqc_status = "pending"

        self.add_domain_event(DomainEvent(
            event_type="purchase_order.received",
            aggregate_id=self.id,
            payload={"order_id": self.id, "iqc_required": self.iqc_required},
        ))

    def close(self) -> None:
        if self.status != OrderStatus.RECEIVED:
            raise ValueError(f"Cannot close order in {self.status.value} status")
        self.status = OrderStatus.CLOSED

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)