from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class AppType(str, Enum):
    INTEGRATION = "integration"
    VISUALIZATION = "visualization"
    ANALYSIS = "analysis"
    AUTOMATION = "automation"
    CUSTOM_WIDGET = "custom_widget"


class AppStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PUBLISHED = "published"
    REVOKED = "revoked"


class DeveloperTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class UsageStats:
    total_calls: int = 0
    active_users: int = 0
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "active_users": self.active_users,
            "error_rate": round(self.error_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
        }


@dataclass
class ApiKey:
    key_id: str
    key_prefix: str
    scopes: list[str] = field(default_factory=list)
    rate_limit: int = 1000
    created_at: str = ""
    revoked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_id": self.key_id,
            "key_prefix": self.key_prefix,
            "scopes": self.scopes,
            "rate_limit": self.rate_limit,
            "created_at": self.created_at,
            "revoked": self.revoked,
        }


class DeveloperApp(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        developer_id: str,
        name: str,
        description: str,
        app_type: AppType,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.developer_id = developer_id
        self.name = name
        self.description = description
        self.app_type = app_type
        self.api_scopes: list[str] = []
        self.webhook_urls: list[str] = []
        self.status = AppStatus.DRAFT
        self.version = "1.0.0"
        self.published_at: datetime | None = None
        self.usage_stats = UsageStats()
        self.created_at = datetime.now(timezone.utc)

    def submit(self) -> None:
        self.status = AppStatus.SUBMITTED

    def approve(self) -> None:
        self.status = AppStatus.APPROVED

    def publish(self) -> None:
        self.status = AppStatus.PUBLISHED
        self.published_at = datetime.now(timezone.utc)

    def revoke(self) -> None:
        self.status = AppStatus.REVOKED

    def update_usage(self, calls: int, errors: float, latency: float) -> None:
        self.usage_stats.total_calls = calls
        self.usage_stats.error_rate = errors
        self.usage_stats.avg_latency_ms = latency

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "developer_id": self.developer_id,
            "name": self.name,
            "app_type": self.app_type.value,
            "status": self.status.value,
            "version": self.version,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat(),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "description": self.description,
            "api_scopes": self.api_scopes,
            "webhook_urls": self.webhook_urls,
            "usage_stats": self.usage_stats.to_dict(),
        })
        return base