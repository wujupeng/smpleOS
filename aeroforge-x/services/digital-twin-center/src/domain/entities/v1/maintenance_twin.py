from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class MaintenanceTwinStatus(str, Enum):
    SERVICEABLE = "serviceable"
    MAINTENANCE_DUE = "maintenance_due"
    UNDER_MAINTENANCE = "under_maintenance"
    UNSERVICEABLE = "unserviceable"


@dataclass
class MaintenanceRecord:
    maintenance_id: str
    maintenance_type: str
    description: str
    performed_date: str
    technician: str
    findings: list[str] = field(default_factory=list)
    corrective_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "maintenance_id": self.maintenance_id,
            "maintenance_type": self.maintenance_type,
            "description": self.description,
            "performed_date": self.performed_date,
            "technician": self.technician,
            "findings": self.findings,
            "corrective_actions": self.corrective_actions,
        }


@dataclass
class ComponentReplacement:
    component_id: str
    component_name: str
    old_serial: str
    new_serial: str
    replacement_date: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "old_serial": self.old_serial,
            "new_serial": self.new_serial,
            "replacement_date": self.replacement_date,
            "reason": self.reason,
        }


@dataclass
class RemainingLife:
    component_id: str
    component_name: str
    total_life_hours: float
    consumed_hours: float
    remaining_hours: float
    remaining_percentage: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "total_life_hours": self.total_life_hours,
            "consumed_hours": self.consumed_hours,
            "remaining_hours": self.remaining_hours,
            "remaining_percentage": self.remaining_percentage,
        }


@dataclass
class HealthIndicator:
    system_name: str
    health_score: float
    trend: str
    last_check_date: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_name": self.system_name,
            "health_score": self.health_score,
            "trend": self.trend,
            "last_check_date": self.last_check_date,
        }


class MaintenanceTwin:
    def __init__(
        self,
        aircraft_serial_number: str,
        twin_id: str | None = None,
    ) -> None:
        self.twin_id: str = twin_id or str(uuid4())
        self.aircraft_serial_number: str = aircraft_serial_number
        self.maintenance_history: list[MaintenanceRecord] = []
        self.component_replacements: list[ComponentReplacement] = []
        self.remaining_life: list[RemainingLife] = []
        self.health_indicators: list[HealthIndicator] = []
        self.status: MaintenanceTwinStatus = MaintenanceTwinStatus.SERVICEABLE
        self.last_sync_time: datetime | None = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def add_maintenance_record(self, record: MaintenanceRecord) -> None:
        self.maintenance_history.append(record)
        self.last_sync_time = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def add_component_replacement(self, replacement: ComponentReplacement) -> None:
        self.component_replacements.append(replacement)
        self._update_remaining_life_after_replacement(replacement.component_id)
        self.updated_at = datetime.now(timezone.utc)

    def _update_remaining_life_after_replacement(self, component_id: str) -> None:
        for rl in self.remaining_life:
            if rl.component_id == component_id:
                rl.consumed_hours = 0.0
                rl.remaining_hours = rl.total_life_hours
                rl.remaining_percentage = 100.0

    def update_remaining_life(self, component_id: str, consumed_hours: float) -> None:
        for rl in self.remaining_life:
            if rl.component_id == component_id:
                rl.consumed_hours = consumed_hours
                rl.remaining_hours = rl.total_life_hours - consumed_hours
                rl.remaining_percentage = (rl.remaining_hours / rl.total_life_hours) * 100 if rl.total_life_hours > 0 else 0
                if rl.remaining_percentage < 20:
                    self.status = MaintenanceTwinStatus.MAINTENANCE_DUE
                break
        self.updated_at = datetime.now(timezone.utc)

    def update_health_indicator(self, indicator: HealthIndicator) -> None:
        existing = [h for h in self.health_indicators if h.system_name == indicator.system_name]
        if existing:
            idx = self.health_indicators.index(existing[0])
            self.health_indicators[idx] = indicator
        else:
            self.health_indicators.append(indicator)
        self._evaluate_overall_status()
        self.updated_at = datetime.now(timezone.utc)

    def _evaluate_overall_status(self) -> None:
        if not self.health_indicators:
            return
        min_health = min(h.health_score for h in self.health_indicators)
        if min_health < 30:
            self.status = MaintenanceTwinStatus.UNSERVICEABLE
        elif min_health < 60:
            self.status = MaintenanceTwinStatus.MAINTENANCE_DUE
        else:
            self.status = MaintenanceTwinStatus.SERVICEABLE

    def sync_from_maintenance(self, records: list[MaintenanceRecord], replacements: list[ComponentReplacement], life_updates: list[RemainingLife]) -> None:
        self.maintenance_history.extend(records)
        self.component_replacements.extend(replacements)
        for rl in life_updates:
            existing = [r for r in self.remaining_life if r.component_id == rl.component_id]
            if existing:
                idx = self.remaining_life.index(existing[0])
                self.remaining_life[idx] = rl
            else:
                self.remaining_life.append(rl)
        self.last_sync_time = datetime.now(timezone.utc)
        self._evaluate_overall_status()
        self.updated_at = datetime.now(timezone.utc)

    def get_components_due_for_replacement(self, threshold_percentage: float = 20.0) -> list[RemainingLife]:
        return [rl for rl in self.remaining_life if rl.remaining_percentage <= threshold_percentage]

    def to_dict(self) -> dict[str, Any]:
        return {
            "twin_id": self.twin_id,
            "aircraft_serial_number": self.aircraft_serial_number,
            "maintenance_history": [r.to_dict() for r in self.maintenance_history],
            "component_replacements": [r.to_dict() for r in self.component_replacements],
            "remaining_life": [r.to_dict() for r in self.remaining_life],
            "health_indicators": [h.to_dict() for h in self.health_indicators],
            "status": self.status.value,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }