from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.purchase_order import OrderStatus
from ..domain.services.purchase_domain_service import PurchaseDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/supply", tags=["Supply Chain - Purchase & Inventory"])

_service = PurchaseDomainService()


class OrderItemRequest(BaseModel):
    material_code: str = Field(..., min_length=1)
    material_name: str = ""
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(default=0.0, ge=0)
    unit: str = "pcs"
    delivery_date: str = ""


class CreatePurchaseOrderRequest(BaseModel):
    tenant_id: str = Field(default="default")
    supplier_id: str = Field(..., min_length=1)
    supplier_name: str = ""
    order_items: list[OrderItemRequest] = Field(..., min_length=1)
    currency: str = "CNY"
    payment_terms: str = "net30"
    expected_delivery_date: str = ""
    iqc_required: bool = True
    created_by: str = ""


class ReceiveGoodsRequest(BaseModel):
    received_items: list[dict[str, Any]] | None = None


class CreateInventoryItemRequest(BaseModel):
    tenant_id: str = Field(default="default")
    item_code: str = Field(..., min_length=1)
    item_name: str = Field(..., min_length=1)
    warehouse_location: str = ""
    reorder_point: int = Field(default=10, ge=0)
    safety_stock: int = Field(default=5, ge=0)
    unit_cost: float = Field(default=0.0, ge=0)
    unit: str = "pcs"
    material_type: str = ""


@router.post("/orders", response_model=ApiResponse[dict])
async def create_purchase_order(body: CreatePurchaseOrderRequest):
    order = _service.create_purchase_order(
        tenant_id=body.tenant_id,
        supplier_id=body.supplier_id,
        supplier_name=body.supplier_name,
        order_items=[item.model_dump() for item in body.order_items],
        currency=body.currency,
        payment_terms=body.payment_terms,
        expected_delivery_date=body.expected_delivery_date,
        iqc_required=body.iqc_required,
        created_by=body.created_by,
    )
    return ApiResponse(data=order.to_dict())


@router.get("/orders", response_model=ApiResponse[dict])
async def list_purchase_orders(
    tenant_id: str | None = None,
    supplier_id: str | None = None,
    status: OrderStatus | None = None,
):
    orders = _service.list_orders(tenant_id, supplier_id, status)
    return ApiResponse(data={
        "total": len(orders),
        "orders": [o.to_dict() for o in orders],
    })


@router.get("/orders/{order_id}", response_model=ApiResponse[dict])
async def get_purchase_order(order_id: str):
    order = _service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return ApiResponse(data=order.to_dict())


@router.post("/orders/{order_id}/submit", response_model=ApiResponse[dict])
async def submit_purchase_order(order_id: str):
    order = _service.submit_purchase_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return ApiResponse(data=order.to_dict())


@router.post("/orders/{order_id}/confirm", response_model=ApiResponse[dict])
async def confirm_purchase_order(order_id: str):
    order = _service.confirm_purchase_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return ApiResponse(data=order.to_dict())


@router.post("/orders/{order_id}/ship", response_model=ApiResponse[dict])
async def ship_purchase_order(order_id: str):
    order = _service.ship_purchase_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return ApiResponse(data=order.to_dict())


@router.post("/orders/{order_id}/receive", response_model=ApiResponse[dict])
async def receive_goods(order_id: str, body: ReceiveGoodsRequest):
    order = _service.receive_goods(order_id, body.received_items)
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return ApiResponse(data=order.to_dict())


@router.post("/inventory", response_model=ApiResponse[dict])
async def create_inventory_item(body: CreateInventoryItemRequest):
    item = _service.create_inventory_item(
        tenant_id=body.tenant_id,
        item_code=body.item_code,
        item_name=body.item_name,
        warehouse_location=body.warehouse_location,
        reorder_point=body.reorder_point,
        safety_stock=body.safety_stock,
        unit_cost=body.unit_cost,
        unit=body.unit,
        material_type=body.material_type,
    )
    return ApiResponse(data=item.to_dict())


@router.get("/inventory", response_model=ApiResponse[dict])
async def list_inventory(
    tenant_id: str | None = None,
    below_reorder: bool = False,
):
    items = _service.list_inventory(tenant_id, below_reorder)
    return ApiResponse(data={
        "total": len(items),
        "items": [i.to_dict() for i in items],
    })


@router.get("/inventory/{item_id}", response_model=ApiResponse[dict])
async def get_inventory_item(item_id: str):
    item = _service.get_inventory_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return ApiResponse(data=item.to_dict())


@router.get("/inventory/reorder-advice", response_model=ApiResponse[dict])
async def get_reorder_advice(tenant_id: str | None = None):
    advice_list = _service.generate_reorder_advice(tenant_id)
    return ApiResponse(data={
        "total": len(advice_list),
        "advice": [a.to_dict() for a in advice_list],
    })