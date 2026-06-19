from __future__ import annotations

import logging
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .entities.supplier import (
    Supplier, SupplierCategory, QualificationStatus,
    ContactInfo, PerformanceMetrics, Certification,
)

logger = logging.getLogger(__name__)


class SupplierDomainService:
    def __init__(self) -> None:
        self._suppliers: dict[str, Supplier] = {}

    def create_supplier(
        self,
        tenant_id: str,
        name: str,
        code: str,
        category: SupplierCategory = SupplierCategory.RAW_MATERIAL,
        contact_info: ContactInfo | None = None,
        lead_time_days: int = 30,
        min_order_quantity: int = 1,
        supplied_materials: list[str] | None = None,
    ) -> Supplier:
        supplier = Supplier(
            tenant_id=tenant_id,
            name=name,
            code=code,
            category=category,
            contact_info=contact_info or ContactInfo(),
            lead_time_days=lead_time_days,
            min_order_quantity=min_order_quantity,
            supplied_materials=supplied_materials or [],
        )
        self._suppliers[supplier.id] = supplier

        supplier.add_domain_event(DomainEvent(
            event_type="supplier.created",
            aggregate_id=supplier.id,
            payload={"supplier_id": supplier.id, "name": name, "code": code},
        ))

        logger.info("Created supplier %s (%s)", supplier.id, code)
        return supplier

    def update_supplier(
        self,
        supplier_id: str,
        name: str | None = None,
        contact_info: ContactInfo | None = None,
        lead_time_days: int | None = None,
        min_order_quantity: int | None = None,
        supplied_materials: list[str] | None = None,
        notes: str | None = None,
    ) -> Supplier | None:
        supplier = self._suppliers.get(supplier_id)
        if supplier is None:
            return None

        if name is not None:
            supplier.name = name
        if contact_info is not None:
            supplier.contact_info = contact_info
        if lead_time_days is not None:
            supplier.lead_time_days = lead_time_days
        if min_order_quantity is not None:
            supplier.min_order_quantity = min_order_quantity
        if supplied_materials is not None:
            supplier.supplied_materials = supplied_materials
        if notes is not None:
            supplier.notes = notes

        from datetime import datetime, timezone
        supplier.updated_at = datetime.now(timezone.utc).isoformat()

        return supplier

    def qualify_supplier(self, supplier_id: str) -> Supplier | None:
        supplier = self._suppliers.get(supplier_id)
        if supplier is None:
            return None
        supplier.qualify()
        return supplier

    def disqualify_supplier(self, supplier_id: str, reason: str = "") -> Supplier | None:
        supplier = self._suppliers.get(supplier_id)
        if supplier is None:
            return None
        supplier.disqualify(reason)
        return supplier

    def evaluate_performance(
        self,
        supplier_id: str,
        on_time_rate: float,
        quality_rate: float,
        response_days: float,
    ) -> Supplier | None:
        supplier = self._suppliers.get(supplier_id)
        if supplier is None:
            return None
        supplier.update_performance(on_time_rate, quality_rate, response_days)
        return supplier

    def select_supplier(
        self,
        material_code: str | None = None,
        category: SupplierCategory | None = None,
        min_score: float = 0.0,
    ) -> list[Supplier]:
        candidates = list(self._suppliers.values())

        if material_code:
            candidates = [s for s in candidates if material_code in s.supplied_materials]

        if category:
            candidates = [s for s in candidates if s.category == category]

        candidates = [s for s in candidates if s.qualification_status == QualificationStatus.QUALIFIED]

        candidates = [s for s in candidates if s.performance_metrics.overall_score >= min_score]

        candidates.sort(key=lambda s: s.performance_metrics.overall_score, reverse=True)

        return candidates

    def add_certification(
        self,
        supplier_id: str,
        cert: Certification,
    ) -> Supplier | None:
        supplier = self._suppliers.get(supplier_id)
        if supplier is None:
            return None
        supplier.add_certification(cert)
        return supplier

    def get_supplier(self, supplier_id: str) -> Supplier | None:
        return self._suppliers.get(supplier_id)

    def list_suppliers(
        self,
        tenant_id: str | None = None,
        category: SupplierCategory | None = None,
        qualification_status: QualificationStatus | None = None,
    ) -> list[Supplier]:
        suppliers = list(self._suppliers.values())
        if tenant_id:
            suppliers = [s for s in suppliers if s.tenant_id == tenant_id]
        if category:
            suppliers = [s for s in suppliers if s.category == category]
        if qualification_status:
            suppliers = [s for s in suppliers if s.qualification_status == qualification_status]
        return suppliers