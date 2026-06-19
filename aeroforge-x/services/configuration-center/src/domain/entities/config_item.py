from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any

from ..value_objects.config_item_type import ConfigItemType
from ..value_objects.config_item_status import ConfigItemStatus
from ..value_objects.propagation_action import PropagationAction


@dataclass
class ConfigItem:
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    item_number: str = ""
    item_name: str = ""
    item_type: str = ""
    description: str = ""
    current_version: int = 1
    status: str = ConfigItemStatus.DRAFT
    lifecycle: str = "development"
    owner_id: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def transition_lifecycle(self, new_lifecycle: str) -> None:
        valid_transitions = {
            "development": ["production"],
            "production": ["service"],
            "service": ["retired"],
        }
        if new_lifecycle not in valid_transitions.get(self.lifecycle, []):
            raise ValueError(f"Cannot transition from {self.lifecycle} to {new_lifecycle}")
        self.lifecycle = new_lifecycle
        self.updated_at = datetime.now(timezone.utc)

    def release(self) -> None:
        if self.status != ConfigItemStatus.DRAFT:
            raise ValueError(f"Cannot release item in {self.status} status")
        self.status = ConfigItemStatus.RELEASED
        self.updated_at = datetime.now(timezone.utc)

    def baseline(self) -> None:
        if self.status != ConfigItemStatus.RELEASED:
            raise ValueError(f"Cannot baseline item in {self.status} status")
        self.status = ConfigItemStatus.BASELINED
        self.updated_at = datetime.now(timezone.utc)

    def obsolete(self) -> None:
        self.status = ConfigItemStatus.OBSOLETE
        self.updated_at = datetime.now(timezone.utc)

    def update_properties(self, new_props: dict) -> None:
        if self.status == ConfigItemStatus.BASELINED:
            raise ValueError("Cannot modify baselined item - submit a change request")
        self.properties.update(new_props)
        self.current_version += 1
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "item_number": self.item_number,
            "item_name": self.item_name,
            "item_type": self.item_type,
            "current_version": self.current_version,
            "status": self.status,
            "lifecycle": self.lifecycle,
            "owner_id": self.owner_id,
            "properties": self.properties,
        }