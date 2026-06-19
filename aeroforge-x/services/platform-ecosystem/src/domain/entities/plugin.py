from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class PluginType(str, Enum):
    DATA_SOURCE = "data_source"
    VISUALIZATION = "visualization"
    ANALYSIS = "analysis"
    WORKFLOW = "workflow"
    CUSTOM_PANEL = "custom_panel"


class PriceModel(str, Enum):
    FREE = "free"
    FREEMIUM = "freemium"
    PAID = "paid"
    SUBSCRIPTION = "subscription"


class PluginStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


@dataclass
class PluginManifest:
    entry_point: str = ""
    permissions: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)
    min_platform_version: str = "4.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_point": self.entry_point,
            "permissions": self.permissions,
            "config_schema": self.config_schema,
            "min_platform_version": self.min_platform_version,
        }


class Plugin(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        developer_id: str,
        name: str,
        description: str,
        plugin_type: PluginType,
        price_model: PriceModel = PriceModel.FREE,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.developer_id = developer_id
        self.name = name
        self.description = description
        self.plugin_type = plugin_type
        self.price_model = price_model
        self.version = "1.0.0"
        self.min_platform_version = "4.0.0"
        self.install_count = 0
        self.rating: float = 0.0
        self.rating_count = 0
        self.status = PluginStatus.PENDING_REVIEW
        self.manifest = PluginManifest()
        self.created_at = datetime.now(timezone.utc)

    def approve_and_publish(self) -> None:
        self.status = PluginStatus.PUBLISHED

    def deprecate(self) -> None:
        self.status = PluginStatus.DEPRECATED

    def remove(self) -> None:
        self.status = PluginStatus.REMOVED

    def increment_install(self) -> None:
        self.install_count += 1

    def decrement_install(self) -> None:
        self.install_count = max(0, self.install_count - 1)

    def add_rating(self, score: float) -> None:
        total = self.rating * self.rating_count + score
        self.rating_count += 1
        self.rating = round(total / self.rating_count, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "developer_id": self.developer_id,
            "name": self.name,
            "plugin_type": self.plugin_type.value,
            "price_model": self.price_model.value,
            "version": self.version,
            "install_count": self.install_count,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "description": self.description,
            "manifest": self.manifest.to_dict(),
        })
        return base