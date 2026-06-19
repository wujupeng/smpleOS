import pytest

from aeroforge_common.tenant.context import (
    TenantContext, TenantInfo, get_current_tenant_id,
    set_tenant_context, clear_tenant_context,
)
from aeroforge_common.tenant.schema_isolator import (
    TenantSchemaIsolator, get_tenant_schema, get_tenant_bucket_prefix,
    get_tenant_neo4j_label,
)


class TestTenantContext:
    def test_set_and_get(self) -> None:
        info = set_tenant_context("t-001", "acme")
        assert info.tenant_id == "t-001"
        assert info.tenant_code == "acme"
        assert info.schema_name == "tenant_acme"
        assert info.bucket_prefix == "t-001/"

    def test_get_current_tenant_id(self) -> None:
        set_tenant_context("t-002", "beta")
        assert get_current_tenant_id() == "t-002"
        clear_tenant_context()

    def test_get_current_tenant_id_none(self) -> None:
        clear_tenant_context()
        assert get_current_tenant_id() is None

    def test_get_required_raises_when_not_set(self) -> None:
        clear_tenant_context()
        with pytest.raises(RuntimeError, match="Tenant context not set"):
            TenantContext.get_required()

    def test_clear(self) -> None:
        set_tenant_context("t-003", "gamma")
        clear_tenant_context()
        assert TenantContext.get() is None

    def test_schema_name_format(self) -> None:
        info = set_tenant_context("t-004", "my_company")
        assert info.schema_name == "tenant_my_company"

    def test_bucket_prefix_format(self) -> None:
        info = set_tenant_context("t-005", "delta")
        assert info.bucket_prefix == "t-005/"

    def test_different_tenants_isolated(self) -> None:
        info_a = set_tenant_context("t-a", "company_a")
        assert info_a.tenant_id == "t-a"

        info_b = set_tenant_context("t-b", "company_b")
        assert info_b.tenant_id == "t-b"
        assert info_b.schema_name == "tenant_company_b"

        clear_tenant_context()


class TestTenantSchemaIsolator:
    def test_get_schema_name(self) -> None:
        isolator = TenantSchemaIsolator()
        assert isolator.get_schema_name("acme") == "tenant_acme"

    def test_get_public_schema(self) -> None:
        isolator = TenantSchemaIsolator()
        assert isolator.get_public_schema() == "public"

    def test_get_current_schema_with_tenant(self) -> None:
        set_tenant_context("t-001", "acme")
        assert get_tenant_schema() == "tenant_acme"
        clear_tenant_context()

    def test_get_current_schema_without_tenant(self) -> None:
        clear_tenant_context()
        assert get_tenant_schema() == "public"

    def test_build_search_path(self) -> None:
        isolator = TenantSchemaIsolator()
        result = isolator.build_schema_search_path("tenant_acme")
        assert "tenant_acme" in result
        assert "public" in result

    def test_get_bucket_prefix(self) -> None:
        isolator = TenantSchemaIsolator()
        assert isolator.get_bucket_prefix("t-001") == "t-001/"

    def test_get_current_bucket_prefix(self) -> None:
        set_tenant_context("t-001", "acme")
        assert get_tenant_bucket_prefix() == "t-001/"
        clear_tenant_context()

    def test_get_neo4j_label(self) -> None:
        isolator = TenantSchemaIsolator()
        assert isolator.get_neo4j_tenant_label("t-001") == "Tenant_t-001"

    def test_get_current_neo4j_label(self) -> None:
        set_tenant_context("t-001", "acme")
        assert get_tenant_neo4j_label() == "Tenant_t-001"
        clear_tenant_context()