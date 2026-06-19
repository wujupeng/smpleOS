from __future__ import annotations

import logging
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .entities.purchase_order import PurchaseOrder, OrderStatus, OrderItem
from .entities.inventory_item import InventoryItem

logger = logging.getLogger(__name__)


class ReorderAdvice:
    def __init__(self, item: InventoryItem, suggested_quantity: int, reason: str) -> None:
        self.item_code = item.item_code
        self.item_name = item.item_name
        self.current_available = item.quantity_available
        self.reorder_point = item.reorder_point
        self.safety_stock = item.safety_stock
        self.suggested_quantity = suggested_quantity
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_code": self.item_code,
            "item_name": self.item_name,
            "current_available": self.current_available,
            "reorder_point": self.reorder_point,
            "safety_stock": self.safety_stock,
            "suggested_quantity": self.suggested_quantity,
            "reason": self.reason,
        }


class PurchaseDomainService:
    def __init__(self) -> None:
        self._orders: dict[str, PurchaseOrder] = {}
        self._inventory: dict[str, InventoryItem] = {}
        self._order_counter = 0

    def create_purchase_order(
        self,
        tenant_id: str,
        supplier_id: str,
        supplier_name: str,
        order_items: list[dict[str, Any]],
        currency: str = "CNY",
        payment_terms: str = "net30",
        expected_delivery_date: str = "",
        iqc_required: bool = True,
        created_by: str = "",
    ) -> PurchaseOrder:
        self._order_counter += 1
        order_code = f"PO-{self._order_counter:06d}"

        items = []
        for item_data in order_items:
            items.append(OrderItem(
                material_code=item_data.get("material_code", ""),
                material_name=item_data.get("material_name", ""),
                quantity=item_data.get("quantity", 1),
                unit_price=item_data.get("unit_price", 0.0),
                unit=item_data.get("unit", "pcs"),
                delivery_date=item_data.get("delivery_date", ""),
            ))

        order = PurchaseOrder(
            tenant_id=tenant_id,
            order_code=order_code,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            order_items=items,
            currency=currency,
            payment_terms=payment_terms,
            expected_delivery_date=expected_delivery_date,
            iqc_required=iqc_required,
            created_by=created_by,
        )
        order.compute_total()

        self._orders[order.id] = order

        order.add_domain_event(DomainEvent(
            event_type="purchase_order.created",
            aggregate_id=order.id,
            payload={"order_code": order_code, "supplier_id": supplier_id},
        ))

        logger.info("Created purchase order %s", order_code)
        return order

    def submit_purchase_order(self, order_id: str) -> PurchaseOrder | None:
        order = self._orders.get(order_id)
        if order is None:
            return None
        order.submit()
        return order

    def confirm_purchase_order(self, order_id: str) -> PurchaseOrder | None:
        order = self._orders.get(order_id)
        if order is None:
            return None
        order.confirm()
        return order

    def ship_purchase_order(self, order_id: str) -> PurchaseOrder | None:
        order = self._orders.get(order_id)
        if order is None:
            return None
        order.ship()
        return order

    def receive_goods(
        self,
        order_id: str,
        received_items: list[dict[str, int]] | None = None,
    ) -> PurchaseOrder | None:
        order = self._orders.get(order_id)
        if order is None:
            return None

        order.receive(received_items)

        for item in order.order_items:
            inventory = self._find_or_create_inventory(
                tenant_id=order.tenant_id,
                material_code=item.material_code,
                material_name=item.material_name,
            )
            received_qty = item.received_quantity if item.received_quantity > 0 else item.quantity
            inventory.receive_stock(received_qty)

        return order

    def get_order(self, order_id: str) -> PurchaseOrder | None:
        return self._orders.get(order_id)

    def list_orders(
        self,
        tenant_id: str | None = None,
        supplier_id: str | None = None,
        status: OrderStatus | None = None,
    ) -> list[PurchaseOrder]:
        orders = list(self._orders.values())
        if tenant_id:
            orders = [o for o in orders if o.tenant_id == tenant_id]
        if supplier_id:
            orders = [o for o in orders if o.supplier_id == supplier_id]
        if status:
            orders = [o for o in orders if o.status == status]
        return orders

    def create_inventory_item(
        self,
        tenant_id: str,
        item_code: str,
        item_name: str,
        warehouse_location: str = "",
        reorder_point: int = 10,
        safety_stock: int = 5,
        unit_cost: float = 0.0,
        unit: str = "pcs",
        material_type: str = "",
    ) -> InventoryItem:
        item = InventoryItem(
            tenant_id=tenant_id,
            item_code=item_code,
            item_name=item_name,
            warehouse_location=warehouse_location,
            reorder_point=reorder_point,
            safety_stock=safety_stock,
            unit_cost=unit_cost,
            unit=unit,
            material_type=material_type,
        )
        self._inventory[item.id] = item
        return item

    def get_inventory_item(self, item_id: str) -> InventoryItem | None:
        return self._inventory.get(item_id)

    def find_inventory_by_code(self, item_code: str) -> InventoryItem | None:
        for item in self._inventory.values():
            if item.item_code == item_code:
                return item
        return None

    def list_inventory(
        self,
        tenant_id: str | None = None,
        below_reorder: bool = False,
    ) -> list[InventoryItem]:
        items = list(self._inventory.values())
        if tenant_id:
            items = [i for i in items if i.tenant_id == tenant_id]
        if below_reorder:
            items = [i for i in items if i.is_below_reorder]
        return items

    def check_inventory(self, item_code: str) -> InventoryItem | None:
        return self.find_inventory_by_code(item_code)

    def generate_reorder_advice(self, tenant_id: str | None = None) -> list[ReorderAdvice]:
        items = self.list_inventory(tenant_id=tenant_id, below_reorder=True)
        advice_list = []

        for item in items:
            if item.is_below_safety:
                suggested = item.reorder_point * 3 - item.quantity_available
                reason = "低于安全库存，需紧急补货"
            else:
                suggested = item.reorder_point * 2 - item.quantity_available
                reason = "低于再订购点，建议补货"

            suggested = max(suggested, item.reorder_point)
            advice_list.append(ReorderAdvice(item=item, suggested_quantity=suggested, reason=reason))

        return advice_list

    def _find_or_create_inventory(
        self,
        tenant_id: str,
        material_code: str,
        material_name: str = "",
    ) -> InventoryItem:
        existing = self.find_inventory_by_code(material_code)
        if existing:
            return existing

        item = InventoryItem(
            tenant_id=tenant_id,
            item_code=material_code,
            item_name=material_name or material_code,
        )
        self._inventory[item.id] = item
        return item