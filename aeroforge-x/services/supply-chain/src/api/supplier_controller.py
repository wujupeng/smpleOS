from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.supplier import (
    SupplierCategory, QualificationStatus, ContactInfo, Certification,
)
from ..domain.services.supplier_domain_service import SupplierDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/supply", tags=["Supply Chain - Suppliers"])

_service = SupplierDomainService()


class ContactInfoRequest(BaseModel):
    contact_person: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""


class CertificationRequest(BaseModel):
    name: str
    certificate_number: str = ""
    issued_by: str = ""
    issued_date: str = ""
    expiry_date: str = ""


class CreateSupplierRequest(BaseModel):
    tenant_id: str = Field(default="default")
    name: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    category: SupplierCategory = SupplierCategory.RAW_MATERIAL
    contact_info: ContactInfoRequest | None = None
    lead_time_days: int = 30
    min_order_quantity: int = 1
    supplied_materials: list[str] = Field(default_factory=list)


class UpdateSupplierRequest(BaseModel):
    name: str | None = None
    contact_info: ContactInfoRequest | None = None
    lead_time_days: int | None = None
    min_order_quantity: int | None = None
    supplied_materials: list[str] | None = None
    notes: str | None = None


class EvaluatePerformanceRequest(BaseModel):
    on_time_delivery_rate: float = Field(..., ge=0, le=1)
    quality_pass_rate: float = Field(..., ge=0, le=1)
    avg_response_time_days: float = Field(..., ge=0)


class SelectSupplierRequest(BaseModel):
    material_code: str | None = None
    category: SupplierCategory | None = None
    min_score: float = 0.0


@router.post("/suppliers", response_model=ApiResponse[dict])
async def create_supplier(body: CreateSupplierRequest):
    contact = ContactInfo(**body.contact_info.model_dump()) if body.contact_info else None
    supplier = _service.create_supplier(
        tenant_id=body.tenant_id,
        name=body.name,
        code=body.code,
        category=body.category,
        contact_info=contact,
        lead_time_days=body.lead_time_days,
        min_order_quantity=body.min_order_quantity,
        supplied_materials=body.supplied_materials,
    )
    return ApiResponse(data=supplier.to_dict())


@router.get("/suppliers", response_model=ApiResponse[dict])
async def list_suppliers(
    tenant_id: str | None = None,
    category: SupplierCategory | None = None,
    qualification_status: QualificationStatus | None = None,
):
    suppliers = _service.list_suppliers(tenant_id, category, qualification_status)
    return ApiResponse(data={
        "total": len(suppliers),
        "suppliers": [s.to_dict() for s in suppliers],
    })


@router.get("/suppliers/{supplier_id}", response_model=ApiResponse[dict])
async def get_supplier(supplier_id: str):
    supplier = _service.get_supplier(supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return ApiResponse(data=supplier.to_dict())


@router.put("/suppliers/{supplier_id}", response_model=ApiResponse[dict])
async def update_supplier(supplier_id: str, body: UpdateSupplierRequest):
    contact = ContactInfo(**body.contact_info.model_dump()) if body.contact_info else None
    supplier = _service.update_supplier(
        supplier_id=supplier_id,
        name=body.name,
        contact_info=contact,
        lead_time_days=body.lead_time_days,
        min_order_quantity=body.min_order_quantity,
        supplied_materials=body.supplied_materials,
        notes=body.notes,
    )
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return ApiResponse(data=supplier.to_dict())


@router.post("/suppliers/{supplier_id}/qualify", response_model=ApiResponse[dict])
async def qualify_supplier(supplier_id: str):
    supplier = _service.qualify_supplier(supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return ApiResponse(data=supplier.to_dict())


@router.post("/suppliers/{supplier_id}/disqualify", response_model=ApiResponse[dict])
async def disqualify_supplier(supplier_id: str, reason: str = ""):
    supplier = _service.disqualify_supplier(supplier_id, reason)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return ApiResponse(data=supplier.to_dict())


@router.put("/suppliers/{supplier_id}/performance", response_model=ApiResponse[dict])
async def update_performance(supplier_id: str, body: EvaluatePerformanceRequest):
    supplier = _service.evaluate_performance(
        supplier_id=supplier_id,
        on_time_rate=body.on_time_delivery_rate,
        quality_rate=body.quality_pass_rate,
        response_days=body.avg_response_time_days,
    )
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return ApiResponse(data=supplier.to_dict())


@router.post("/suppliers/{supplier_id}/certifications", response_model=ApiResponse[dict])
async def add_certification(supplier_id: str, body: CertificationRequest):
    cert = Certification(**body.model_dump())
    supplier = _service.add_certification(supplier_id, cert)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return ApiResponse(data=supplier.to_dict())


@router.post("/suppliers/select", response_model=ApiResponse[dict])
async def select_supplier(body: SelectSupplierRequest):
    suppliers = _service.select_supplier(
        material_code=body.material_code,
        category=body.category,
        min_score=body.min_score,
    )
    return ApiResponse(data={
        "total": len(suppliers),
        "suppliers": [s.to_dict() for s in suppliers],
    })