from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class DesignTwinStatus(str, Enum):
    ACTIVE = "active"
    OUTDATED = "outdated"
    ARCHIVED = "archived"


@dataclass
class DesignParameter:
    name: str
    value: float
    unit: str
    tolerance: float = 0.0
    source: str = "design"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "tolerance": self.tolerance,
            "source": self.source,
        }


class DesignTwin:
    def __init__(
        self,
        aircraft_serial_number: str,
        twin_id: str | None = None,
    ) -> None:
        self.twin_id: str = twin_id or str(uuid4())
        self.aircraft_serial_number: str = aircraft_serial_number
        self.design_parameters: list[DesignParameter] = []
        self.model_version: int = 1
        self.last_sync_time: datetime | None = None
        self.status: DesignTwinStatus = DesignTwinStatus.ACTIVE
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def add_design_parameter(self, param: DesignParameter) -> None:
        existing = [p for p in self.design_parameters if p.name == param.name]
        if existing:
            idx = self.design_parameters.index(existing[0])
            self.design_parameters[idx] = param
        else:
            self.design_parameters.append(param)
        self.updated_at = datetime.now(timezone.utc)

    def update_from_design_change(self, parameters: list[DesignParameter], version: int) -> None:
        for param in parameters:
            self.add_design_parameter(param)
        self.model_version = version
        self.last_sync_time = datetime.now(timezone.utc)
        self.status = DesignTwinStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)

    def mark_outdated(self) -> None:
        self.status = DesignTwinStatus.OUTDATED
        self.updated_at = datetime.now(timezone.utc)

    def get_parameter(self, name: str) -> DesignParameter | None:
        for p in self.design_parameters:
            if p.name == name:
                return p
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "twin_id": self.twin_id,
            "aircraft_serial_number": self.aircraft_serial_number,
            "design_parameters": [p.to_dict() for p in self.design_parameters],
            "model_version": self.model_version,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }