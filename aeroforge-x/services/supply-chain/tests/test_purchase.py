import pytest

from services.supply_chain.src.domain.entities.purchase_order import (
    PurchaseOrder, OrderStatus, OrderItem,
)
from services.supply_chain.src.domain.entities.inventory_item import InventoryItem
from services.supply_chain.src.domain.services.purchase_domain_service import PurchaseDomainService


class TestPurchaseOrderEntity:
    def test_create_order(self) -> None:
        order = PurchaseOrder(order_code="PO-000001", supplier_id="sup-001")
        assert order.status == OrderStatus.DRAFT
        assert order.order_code == "PO-000001"

    def test_submit_order(self) -> None:
        order = PurchaseOrder(order_code="PO-000001", supplier_id="sup-001")
        order.submit()
        assert order.status == OrderStatus.SUBMITTED
        assert len(order.domain_events) == 1

    def test_cannot_submit_non_draft(self) -> None:
        order = PurchaseOrder(order_code="PO-000001", supplier_id="sup-001")
        order.submit()
        with pytest.raises(ValueError):
            order.submit()

    def test_order_lifecycle(self) -> None:
        order = PurchaseOrder(order_code="PO-000001", supplier_id="sup-001")
        order.submit()
        order.confirm()
        assert order.status == OrderStatus.CONFIRMED
        order.ship()
        assert order.status == OrderStatus.IN_TRANSIT
        order.receive()
        assert order.status == OrderStatus.RECEIVED
        assert order.actual_delivery_date != ""
        order.close()
        assert order.status == OrderStatus.CLOSED

    def test_compute_total(self) -> None:
        items = [
            OrderItem(material_code="AL-6061", quantity=100, unit_price=50.0),
            OrderItem(material_code="TI-6AL4V", quantity=20, unit_price=200.0),
        ]
        order = PurchaseOrder(order_code="PO-000001", supplier_id="sup-001", order_items=items)
        total = order.compute_total()
        assert total == 9000.0

    def test_receive_with_iqc(self) -> None:
        order = PurchaseOrder(order_code="PO-000001", supplier_id="sup-001", iqc_required=True)
        order.submit()
        order.confirm()
        order.ship()
        order.receive()
        assert order.iqc_status == "pending"

    def test_receive_without_iqc(self) -> None:
        order = PurchaseOrder(order_code="PO-000001", supplier_id="sup-001", iqc_required=False)
        order.submit()
        order.confirm()
        order.ship()
        order.receive()
        assert order.iqc_status == ""

    def test_order_to_dict(self) -> None:
        order = PurchaseOrder(order_code="PO-000001", supplier_id="sup-001", tenant_id="t-001")
        d = order.to_dict()
        assert d["order_code"] == "PO-000001"
        assert d["status"] == "draft"


class TestInventoryItemEntity:
    def test_create_item(self) -> None:
        item = InventoryItem(item_code="AL-6061", item_name="Aluminum 6061")
        assert item.quantity_on_hand == 0
        assert item.quantity_available == 0

    def test_receive_stock(self) -> None:
        item = InventoryItem(item_code="AL-6061", item_name="Aluminum 6061")
        item.receive_stock(100)
        assert item.quantity_on_hand == 100
        assert item.quantity_available == 100
        assert len(item.domain_events) == 1

    def test_reserve_stock(self) -> None:
        item = InventoryItem(item_code="AL-6061", item_name="Aluminum 6061")
        item.receive_stock(100)
        item.reserve_stock(30)
        assert item.quantity_reserved == 30
        assert item.quantity_available == 70

    def test_cannot_reserve_more_than_available(self) -> None:
        item = InventoryItem(item_code="AL-6061", item_name="Aluminum 6061")
        item.receive_stock(50)
        with pytest.raises(ValueError):
            item.reserve_stock(60)

    def test_consume_stock(self) -> None:
        item = InventoryItem(item_code="AL-6061", item_name="Aluminum 6061")
        item.receive_stock(100)
        item.reserve_stock(30)
        item.consume_stock(20)
        assert item.quantity_on_hand == 80
        assert item.quantity_reserved == 10

    def test_below_reorder(self) -> None:
        item = InventoryItem(item_code="AL-6061", item_name="Aluminum 6061",
                             reorder_point=10, safety_stock=5)
        item.receive_stock(8)
        assert item.is_below_reorder is True
        assert item.is_below_safety is False

    def test_below_safety(self) -> None:
        item = InventoryItem(item_code="AL-6061", item_name="Aluminum 6061",
                             reorder_point=10, safety_stock=5)
        item.receive_stock(3)
        assert item.is_below_safety is True

    def test_item_to_dict(self) -> None:
        item = InventoryItem(item_code="AL-6061", item_name="Aluminum 6061", tenant_id="t-001")
        d = item.to_dict()
        assert d["item_code"] == "AL-6061"
        assert "quantity_available" in d
        assert "is_below_reorder" in d


class TestPurchaseDomainService:
    def test_create_purchase_order(self) -> None:
        service = PurchaseDomainService()
        order = service.create_purchase_order(
            tenant_id="t-001",
            supplier_id="sup-001",
            supplier_name="Aero Parts",
            order_items=[
                {"material_code": "AL-6061", "material_name": "Aluminum 6061", "quantity": 100, "unit_price": 50.0},
            ],
        )
        assert order.order_code.startswith("PO-")
        assert order.status == OrderStatus.DRAFT
        assert order.total_amount == 5000.0
        assert len(order.domain_events) == 1

    def test_submit_purchase_order(self) -> None:
        service = PurchaseDomainService()
        order = service.create_purchase_order(
            "t-001", "sup-001", "Test",
            [{"material_code": "AL-6061", "quantity": 10, "unit_price": 50.0}],
        )
        submitted = service.submit_purchase_order(order.id)
        assert submitted.status == OrderStatus.SUBMITTED

    def test_full_order_lifecycle(self) -> None:
        service = PurchaseDomainService()
        order = service.create_purchase_order(
            "t-001", "sup-001", "Aero Parts",
            [{"material_code": "AL-6061", "material_name": "Aluminum 6061", "quantity": 100, "unit_price": 50.0}],
        )
        service.submit_purchase_order(order.id)
        service.confirm_purchase_order(order.id)
        service.ship_purchase_order(order.id)
        received = service.receive_goods(order.id)
        assert received.status == OrderStatus.RECEIVED
        assert received.iqc_status == "pending"

    def test_receive_goods_updates_inventory(self) -> None:
        service = PurchaseDomainService()
        order = service.create_purchase_order(
            "t-001", "sup-001", "Aero Parts",
            [{"material_code": "AL-6061", "material_name": "Aluminum 6061", "quantity": 100, "unit_price": 50.0}],
        )
        service.submit_purchase_order(order.id)
        service.confirm_purchase_order(order.id)
        service.ship_purchase_order(order.id)
        service.receive_goods(order.id)

        inventory = service.find_inventory_by_code("AL-6061")
        assert inventory is not None
        assert inventory.quantity_on_hand == 100

    def test_list_orders(self) -> None:
        service = PurchaseDomainService()
        service.create_purchase_order("t-001", "sup-001", "A", [{"material_code": "M1", "quantity": 10, "unit_price": 10}])
        service.create_purchase_order("t-002", "sup-002", "B", [{"material_code": "M2", "quantity": 20, "unit_price": 20}])
        assert len(service.list_orders()) == 2
        assert len(service.list_orders(tenant_id="t-001")) == 1

    def test_create_inventory_item(self) -> None:
        service = PurchaseDomainService()
        item = service.create_inventory_item(
            tenant_id="t-001",
            item_code="AL-6061",
            item_name="Aluminum 6061",
            reorder_point=20,
            safety_stock=10,
        )
        assert item.item_code == "AL-6061"
        assert item.reorder_point == 20

    def test_reorder_advice(self) -> None:
        service = PurchaseDomainService()
        item = service.create_inventory_item(
            tenant_id="t-001",
            item_code="AL-6061",
            item_name="Aluminum 6061",
            reorder_point=20,
            safety_stock=10,
        )
        item.receive_stock(5)

        advice = service.generate_reorder_advice(tenant_id="t-001")
        assert len(advice) == 1
        assert advice[0].item_code == "AL-6061"
        assert advice[0].suggested_quantity > 0

    def test_reorder_advice_empty_when_stock_ok(self) -> None:
        service = PurchaseDomainService()
        item = service.create_inventory_item(
            tenant_id="t-001",
            item_code="AL-6061",
            item_name="Aluminum 6061",
            reorder_point=10,
        )
        item.receive_stock(50)

        advice = service.generate_reorder_advice(tenant_id="t-001")
        assert len(advice) == 0

    def test_list_inventory_below_reorder(self) -> None:
        service = PurchaseDomainService()
        item1 = service.create_inventory_item("t-001", "M1", "Material 1", reorder_point=10)
        item1.receive_stock(5)
        item2 = service.create_inventory_item("t-001", "M2", "Material 2", reorder_point=10)
        item2.receive_stock(50)

        below = service.list_inventory(below_reorder=True)
        assert len(below) == 1
        assert below[0].item_code == "M1"

    def test_get_order_not_found(self) -> None:
        service = PurchaseDomainService()
        assert service.get_order("nonexistent") is None