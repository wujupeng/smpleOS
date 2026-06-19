from __future__ import annotations

import logging
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .entities.tenant import Tenant, TenantPlan, TenantStatus, PLAN_QUOTAS

logger = logging.getLogger(__name__)


class TenantDomainService:
    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._code_index: dict[str, str] = {}

    def create_tenant(
        self,
        name: str,
        code: str,
        plan: TenantPlan = TenantPlan.STARTER,
    ) -> Tenant:
        if code in self._code_index:
            raise ValueError(f"Tenant code '{code}' already exists")

        plan_config = PLAN_QUOTAS[plan]
        tenant = Tenant(
            name=name,
            code=code,
            status=TenantStatus.ACTIVE,
            plan=plan,
            quota=__import__("dataclasses", fromlist=["TenantQuota"]).TenantQuota(
                max_users=plan_config["max_users"],
                max_projects=plan_config["max_projects"],
                max_storage_gb=plan_config["max_storage_gb"],
            ),
            features=list(plan_config["features"]),
        )

        self._tenants[tenant.id] = tenant
        self._code_index[code] = tenant.id

        tenant.add_domain_event(DomainEvent(
            event_type="tenant.created",
            aggregate_id=tenant.id,
            payload={
                "tenant_id": tenant.id,
                "tenant_code": code,
                "plan": plan.value,
            },
        ))

        logger.info("Created tenant: %s (%s) plan=%s", name, code, plan.value)
        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        return self._tenants.get(tenant_id)

    def get_tenant_by_code(self, code: str) -> Tenant | None:
        tenant_id = self._code_index.get(code)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None

    def list_tenants(self, status: TenantStatus | None = None) -> list[Tenant]:
        tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        return tenants

    def suspend_tenant(self, tenant_id: str, reason: str = "") -> Tenant | None:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            return None
        tenant.suspend(reason)
        return tenant

    def activate_tenant(self, tenant_id: str) -> Tenant | None:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            return None
        tenant.activate()
        return tenant

    def update_tenant_plan(self, tenant_id: str, new_plan: TenantPlan) -> Tenant | None:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            return None
        tenant.update_plan(new_plan)
        return tenant

    def update_tenant(self, tenant_id: str, name: str | None = None) -> Tenant | None:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            return None
        if name is not None:
            tenant.name = name
        from datetime import datetime, timezone
        tenant.updated_at = datetime.now(timezone.utc).isoformat()
        return tenant

    def check_quota(self, tenant_id: str, resource: str, current: int | float) -> dict[str, Any]:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            return {"allowed": False, "reason": "Tenant not found"}
        allowed = tenant.check_quota(resource, current)
        return {
            "allowed": allowed,
            "resource": resource,
            "current": current,
            "limit": getattr(tenant.quota, f"max_{resource}", 0) if not resource.endswith("_gb") else tenant.quota.max_storage_gb,
        }

    def has_feature(self, tenant_id: str, feature_name: str) -> bool:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            return False
        return tenant.has_feature(feature_name)