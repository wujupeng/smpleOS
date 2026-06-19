from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .config_item import ConfigItem


@dataclass
class ConfigBaseline:
    baseline_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    baseline_name: str = ""
    baseline_type: str = "product"
    description: str = ""
    version: int = 1
    status: str = "open"
    frozen_at: datetime | None = None
    frozen_by: str | None = None
    aircraft_config: str | None = None
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _items: dict[str, int] = field(default_factory=dict, repr=False)

    def add_item(self, item: ConfigItem, version: int | None = None) -> None:
        if self.status == "frozen":
            raise ValueError("Cannot add items to a frozen baseline")
        self._items[item.item_id] = version or item.current_version

    def remove_item(self, item_id: str) -> None:
        if self.status == "frozen":
            raise ValueError("Cannot remove items from a frozen baseline")
        if item_id in self._items:
            del self._items[item_id]

    def freeze(self, frozen_by: str) -> None:
        if self.status == "frozen":
            raise ValueError("Baseline is already frozen")
        if not self._items:
            raise ValueError("Cannot freeze empty baseline")
        self.status = "frozen"
        self.frozen_at = datetime.now(timezone.utc)
        self.frozen_by = frozen_by
        self.updated_at = datetime.now(timezone.utc)

    def unfreeze(self) -> None:
        if self.status != "frozen":
            raise ValueError("Baseline is not frozen")
        self.status = "open"
        self.frozen_at = None
        self.frozen_by = None
        self.updated_at = datetime.now(timezone.utc)

    def get_items(self) -> dict[str, int]:
        return dict(self._items)

    def to_dict(self) -> dict:
        return {
            "baseline_id": self.baseline_id,
            "baseline_name": self.baseline_name,
            "baseline_type": self.baseline_type,
            "version": self.version,
            "status": self.status,
            "frozen_at": self.frozen_at.isoformat() if self.frozen_at else None,
            "frozen_by": self.frozen_by,
            "aircraft_config": self.aircraft_config,
            "item_count": len(self._items),
        }