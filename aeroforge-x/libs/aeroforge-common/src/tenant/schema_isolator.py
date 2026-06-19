from __future__ import annotations

import logging
from typing import Any

from .context import TenantContext, TenantInfo

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA = "public"


class TenantSchemaIsolator:
    def get_schema_name(self, tenant_code: str) -> str:
        return f"tenant_{tenant_code}"

    def get_public_schema(self) -> str:
        return DEFAULT_SCHEMA

    def get_current_schema(self) -> str:
        info = TenantContext.get()
        if info and info.status == "active":
            return info.schema_name
        return DEFAULT_SCHEMA

    def build_schema_search_path(self, tenant_schema: str) -> str:
        return f"SET search_path TO {tenant_schema}, {DEFAULT_SCHEMA};"

    def get_bucket_prefix(self, tenant_id: str) -> str:
        return f"{tenant_id}/"

    def get_current_bucket_prefix(self) -> str:
        info = TenantContext.get()
        if info:
            return info.bucket_prefix
        return ""

    def get_neo4j_tenant_label(self, tenant_id: str) -> str:
        return f"Tenant_{tenant_id}"

    def get_current_neo4j_label(self) -> str:
        info = TenantContext.get()
        if info:
            return self.get_neo4j_tenant_label(info.tenant_id)
        return "Tenant_default"


_isolator = TenantSchemaIsolator()


def get_tenant_schema() -> str:
    return _isolator.get_current_schema()


def get_tenant_bucket_prefix() -> str:
    return _isolator.get_current_bucket_prefix()


def get_tenant_neo4j_label() -> str:
    return _isolator.get_current_neo4j_label()