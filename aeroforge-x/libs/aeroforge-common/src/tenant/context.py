from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any


@dataclass
class TenantInfo:
    tenant_id: str
    tenant_code: str
    schema_name: str
    bucket_prefix: str
    plan: str = "starter"
    status: str = "active"


class TenantContext:
    _local = threading.local()

    @classmethod
    def set(cls, tenant_info: TenantInfo | None) -> None:
        cls._local.tenant_info = tenant_info

    @classmethod
    def get(cls) -> TenantInfo | None:
        return getattr(cls._local, "tenant_info", None)

    @classmethod
    def get_required(cls) -> TenantInfo:
        info = cls.get()
        if info is None:
            raise RuntimeError("Tenant context not set. Request must include a valid tenant.")
        return info

    @classmethod
    def clear(cls) -> None:
        if hasattr(cls._local, "tenant_info"):
            delattr(cls._local, "tenant_info")


def get_current_tenant_id() -> str | None:
    info = TenantContext.get()
    return info.tenant_id if info else None


def set_tenant_context(tenant_id: str, tenant_code: str, plan: str = "starter", status: str = "active") -> TenantInfo:
    schema_name = f"tenant_{tenant_code}"
    bucket_prefix = f"{tenant_id}/"
    info = TenantInfo(
        tenant_id=tenant_id,
        tenant_code=tenant_code,
        schema_name=schema_name,
        bucket_prefix=bucket_prefix,
        plan=plan,
        status=status,
    )
    TenantContext.set(info)
    return info


def clear_tenant_context() -> None:
    TenantContext.clear()