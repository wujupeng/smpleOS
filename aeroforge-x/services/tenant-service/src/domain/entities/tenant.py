from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class TenantPlan(str, Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


PLAN_QUOTAS: dict[str, dict[str, Any]] = {
    TenantPlan.STARTER: {
        "max_users": 10,
        "max_projects": 3,
        "max_storage_gb": 50,
        "features": ["design_center", "bom_center", "mes_center"],
    },
    TenantPlan.PROFESSIONAL: {
        "max_users": 50,
        "max_projects": 20,
        "max_storage_gb": 500,
        "features": [
            "design_center", "cae_center", "bom_center", "mes_center",
            "digital_twin_center", "plm_center", "qms_center",
        ],
    },
    TenantPlan.ENTERPRISE: {
        "max_users": 999,
        "max_projects": 999,
        "max_storage_gb": 9999,
        "features": [
            "design_center", "cae_center", "bom_center", "mes_center",
            "digital_twin_center", "plm_center", "qms_center", "ai_engine",
            "supply_chain", "advanced_analytics", "custom_integrations",
        ],
    },
}


@dataclass
class TenantQuota:
    max_users: int = 10
    max_projects: int = 3
    max_storage_gb: int = 50
    current_users: int = 0
    current_projects: int = 0
    current_storage_gb: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_users": self.max_users,
            "max_projects": self.max_projects,
            "max_storage_gb": self.max_storage_gb,
            "current_users": self.current_users,
            "current_projects": self.current_projects,
            "current_storage_gb": self.current_storage_gb,
        }

    def is_within_quota(self, resource: str, current: int | float) -> bool:
        limits = {
            "users": self.max_users,
            "projects": self.max_projects,
            "storage_gb": self.max_storage_gb,
        }
        limit = limits.get(resource, 0)
        return current < limit


@dataclass
class Tenant:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    code: str = ""
    status: TenantStatus = TenantStatus.ACTIVE
    plan: TenantPlan = TenantPlan.STARTER
    quota: TenantQuota = field(default_factory=TenantQuota)
    features: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    expired_at: str = ""
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "status": self.status.value,
            "plan": self.plan.value,
            "quota": self.quota.to_dict(),
            "features": self.features,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expired_at": self.expired_at,
        }

    def suspend(self, reason: str = "") -> None:
        if self.status == TenantStatus.DELETED:
            raise ValueError("Cannot suspend a deleted tenant")
        self.status = TenantStatus.SUSPENDED
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="tenant.suspended",
            aggregate_id=self.id,
            payload={"tenant_id": self.id, "reason": reason},
        ))

    def activate(self) -> None:
        if self.status == TenantStatus.DELETED:
            raise ValueError("Cannot activate a deleted tenant")
        self.status = TenantStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="tenant.activated",
            aggregate_id=self.id,
            payload={"tenant_id": self.id},
        ))

    def update_plan(self, new_plan: TenantPlan) -> None:
        if self.status == TenantStatus.DELETED:
            raise ValueError("Cannot update plan for a deleted tenant")
        old_plan = self.plan
        self.plan = new_plan
        plan_config = PLAN_QUOTAS[new_plan]
        self.quota.max_users = plan_config["max_users"]
        self.quota.max_projects = plan_config["max_projects"]
        self.quota.max_storage_gb = plan_config["max_storage_gb"]
        self.features = list(plan_config["features"])
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="tenant.plan_updated",
            aggregate_id=self.id,
            payload={"tenant_id": self.id, "old_plan": old_plan.value, "new_plan": new_plan.value},
        ))

    def check_quota(self, resource: str, current: int | float) -> bool:
        return self.quota.is_within_quota(resource, current)

    def has_feature(self, feature_name: str) -> bool:
        return feature_name in self.features

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)