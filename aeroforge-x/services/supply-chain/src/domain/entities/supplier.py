from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class SupplierCategory(str, Enum):
    RAW_MATERIAL = "raw_material"
    STANDARD_PART = "standard_part"
    CUSTOM_PART = "custom_part"
    EQUIPMENT = "equipment"


class QualificationStatus(str, Enum):
    QUALIFIED = "qualified"
    CONDITIONAL = "conditional"
    DISQUALIFIED = "disqualified"


@dataclass
class ContactInfo:
    contact_person: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "contact_person": self.contact_person,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
        }


@dataclass
class PerformanceMetrics:
    on_time_delivery_rate: float = 0.0
    quality_pass_rate: float = 0.0
    avg_response_time_days: float = 0.0
    overall_score: float = 0.0
    last_evaluated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "on_time_delivery_rate": self.on_time_delivery_rate,
            "quality_pass_rate": self.quality_pass_rate,
            "avg_response_time_days": self.avg_response_time_days,
            "overall_score": self.overall_score,
            "last_evaluated_at": self.last_evaluated_at,
        }

    def compute_overall_score(self) -> float:
        self.overall_score = round(
            self.on_time_delivery_rate * 0.4
            + self.quality_pass_rate * 0.4
            + max(0, (1.0 - self.avg_response_time_days / 30.0)) * 0.2,
            2,
        )
        return self.overall_score


@dataclass
class Certification:
    name: str = ""
    certificate_number: str = ""
    issued_by: str = ""
    issued_date: str = ""
    expiry_date: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "certificate_number": self.certificate_number,
            "issued_by": self.issued_by,
            "issued_date": self.issued_date,
            "expiry_date": self.expiry_date,
        }

    def is_expired(self) -> bool:
        if not self.expiry_date:
            return False
        return self.expiry_date < datetime.now(timezone.utc).isoformat()


@dataclass
class Supplier:
    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: str = ""
    name: str = ""
    code: str = ""
    category: SupplierCategory = SupplierCategory.RAW_MATERIAL
    qualification_status: QualificationStatus = QualificationStatus.CONDITIONAL
    qualification_date: str = ""
    contact_info: ContactInfo = field(default_factory=ContactInfo)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    certifications: list[Certification] = field(default_factory=list)
    supplied_materials: list[str] = field(default_factory=list)
    lead_time_days: int = 30
    min_order_quantity: int = 1
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "code": self.code,
            "category": self.category.value,
            "qualification_status": self.qualification_status.value,
            "qualification_date": self.qualification_date,
            "contact_info": self.contact_info.to_dict(),
            "performance_metrics": self.performance_metrics.to_dict(),
            "certifications": [c.to_dict() for c in self.certifications],
            "supplied_materials": self.supplied_materials,
            "lead_time_days": self.lead_time_days,
            "min_order_quantity": self.min_order_quantity,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def qualify(self) -> None:
        self.qualification_status = QualificationStatus.QUALIFIED
        self.qualification_date = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="supplier.qualified",
            aggregate_id=self.id,
            payload={"supplier_id": self.id, "name": self.name},
        ))

    def disqualify(self, reason: str = "") -> None:
        self.qualification_status = QualificationStatus.DISQUALIFIED
        self.add_domain_event(DomainEvent(
            event_type="supplier.disqualified",
            aggregate_id=self.id,
            payload={"supplier_id": self.id, "reason": reason},
        ))

    def update_performance(
        self,
        on_time_rate: float,
        quality_rate: float,
        response_days: float,
    ) -> None:
        self.performance_metrics.on_time_delivery_rate = on_time_rate
        self.performance_metrics.quality_pass_rate = quality_rate
        self.performance_metrics.avg_response_time_days = response_days
        self.performance_metrics.last_evaluated_at = datetime.now(timezone.utc).isoformat()
        self.performance_metrics.compute_overall_score()
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def add_certification(self, cert: Certification) -> None:
        self.certifications.append(cert)

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)