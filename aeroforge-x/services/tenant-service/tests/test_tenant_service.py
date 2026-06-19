import pytest

from services.tenant_service.src.domain.entities.tenant import (
    Tenant, TenantPlan, TenantStatus, PLAN_QUOTAS, TenantQuota,
)
from services.tenant_service.src.domain.services.tenant_domain_service import TenantDomainService


class TestTenantEntity:
    def test_create_tenant(self) -> None:
        tenant = Tenant(name="ACME Corp", code="acme", plan=TenantPlan.PROFESSIONAL)
        assert tenant.name == "ACME Corp"
        assert tenant.code == "acme"
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.plan == TenantPlan.PROFESSIONAL

    def test_suspend_tenant(self) -> None:
        tenant = Tenant(name="Test", code="test")
        tenant.suspend(reason="unpaid")
        assert tenant.status == TenantStatus.SUSPENDED
        assert len(tenant.domain_events) == 1
        assert tenant.domain_events[0].event_type == "tenant.suspended"

    def test_activate_tenant(self) -> None:
        tenant = Tenant(name="Test", code="test")
        tenant.suspend("test")
        tenant.activate()
        assert tenant.status == TenantStatus.ACTIVE

    def test_cannot_suspend_deleted(self) -> None:
        tenant = Tenant(name="Test", code="test", status=TenantStatus.DELETED)
        with pytest.raises(ValueError, match="Cannot suspend"):
            tenant.suspend()

    def test_update_plan(self) -> None:
        tenant = Tenant(name="Test", code="test", plan=TenantPlan.STARTER)
        tenant.update_plan(TenantPlan.ENTERPRISE)
        assert tenant.plan == TenantPlan.ENTERPRISE
        assert tenant.quota.max_users == 999
        assert "ai_engine" in tenant.features

    def test_check_quota(self) -> None:
        tenant = Tenant(name="Test", code="test", plan=TenantPlan.STARTER)
        assert tenant.check_quota("users", 5) is True
        assert tenant.check_quota("users", 10) is False

    def test_has_feature(self) -> None:
        tenant = Tenant(name="Test", code="test", plan=TenantPlan.STARTER)
        assert tenant.has_feature("design_center") is True
        assert tenant.has_feature("ai_engine") is False


class TestTenantQuota:
    def test_plan_quotas(self) -> None:
        starter = PLAN_QUOTAS[TenantPlan.STARTER]
        assert starter["max_users"] == 10
        assert starter["max_projects"] == 3

        enterprise = PLAN_QUOTAS[TenantPlan.ENTERPRISE]
        assert enterprise["max_users"] == 999

    def test_is_within_quota(self) -> None:
        quota = TenantQuota(max_users=10, max_projects=3)
        assert quota.is_within_quota("users", 5) is True
        assert quota.is_within_quota("users", 10) is False


class TestTenantDomainService:
    def test_create_tenant(self) -> None:
        service = TenantDomainService()
        tenant = service.create_tenant("ACME", "acme")
        assert tenant.name == "ACME"
        assert tenant.code == "acme"
        assert len(tenant.domain_events) == 1
        assert tenant.domain_events[0].event_type == "tenant.created"

    def test_duplicate_code_rejected(self) -> None:
        service = TenantDomainService()
        service.create_tenant("ACME", "acme")
        with pytest.raises(ValueError, match="already exists"):
            service.create_tenant("Another", "acme")

    def test_get_tenant(self) -> None:
        service = TenantDomainService()
        tenant = service.create_tenant("ACME", "acme")
        found = service.get_tenant(tenant.id)
        assert found is not None
        assert found.name == "ACME"

    def test_get_tenant_by_code(self) -> None:
        service = TenantDomainService()
        service.create_tenant("ACME", "acme")
        found = service.get_tenant_by_code("acme")
        assert found is not None

    def test_suspend_and_activate(self) -> None:
        service = TenantDomainService()
        tenant = service.create_tenant("ACME", "acme")
        service.suspend_tenant(tenant.id, "test")
        assert service.get_tenant(tenant.id).status == TenantStatus.SUSPENDED

        service.activate_tenant(tenant.id)
        assert service.get_tenant(tenant.id).status == TenantStatus.ACTIVE

    def test_update_plan(self) -> None:
        service = TenantDomainService()
        tenant = service.create_tenant("ACME", "acme", plan=TenantPlan.STARTER)
        service.update_tenant_plan(tenant.id, TenantPlan.ENTERPRISE)
        assert service.get_tenant(tenant.id).plan == TenantPlan.ENTERPRISE

    def test_check_quota(self) -> None:
        service = TenantDomainService()
        tenant = service.create_tenant("ACME", "acme", plan=TenantPlan.STARTER)
        result = service.check_quota(tenant.id, "users", 5)
        assert result["allowed"] is True

    def test_has_feature(self) -> None:
        service = TenantDomainService()
        tenant = service.create_tenant("ACME", "acme", plan=TenantPlan.STARTER)
        assert service.has_feature(tenant.id, "design_center") is True
        assert service.has_feature(tenant.id, "ai_engine") is False

    def test_list_tenants(self) -> None:
        service = TenantDomainService()
        service.create_tenant("ACME", "acme")
        service.create_tenant("Beta", "beta")
        assert len(service.list_tenants()) == 2

    def test_list_tenants_by_status(self) -> None:
        service = TenantDomainService()
        t1 = service.create_tenant("ACME", "acme")
        service.create_tenant("Beta", "beta")
        service.suspend_tenant(t1.id)
        active = service.list_tenants(TenantStatus.ACTIVE)
        assert len(active) == 1