from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class FleetTwinStatus(str, Enum):
    ACTIVE = "active"
    PARTIAL = "partial"
    INACTIVE = "inactive"


@dataclass
class FaultStatistics:
    total_faults: int = 0
    critical_faults: int = 0
    faults_by_system: dict[str, int] = field(default_factory=dict)
    faults_by_aircraft: dict[str, int] = field(default_factory=dict)
    mtbf_hours: float = 0.0
    period_start: str = ""
    period_end: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_faults": self.total_faults,
            "critical_faults": self.critical_faults,
            "faults_by_system": self.faults_by_system,
            "faults_by_aircraft": self.faults_by_aircraft,
            "mtbf_hours": self.mtbf_hours,
            "period_start": self.period_start,
            "period_end": self.period_end,
        }


@dataclass
class LifeStatistics:
    total_components: int = 0
    components_due_replacement: int = 0
    average_remaining_life_percentage: float = 0.0
    components_by_remaining_life: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_components": self.total_components,
            "components_due_replacement": self.components_due_replacement,
            "average_remaining_life_percentage": self.average_remaining_life_percentage,
            "components_by_remaining_life": self.components_by_remaining_life,
        }


@dataclass
class MaintenanceStatistics:
    total_maintenance_events: int = 0
    scheduled_events: int = 0
    unscheduled_events: int = 0
    average_turnaround_days: float = 0.0
    maintenance_by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_maintenance_events": self.total_maintenance_events,
            "scheduled_events": self.scheduled_events,
            "unscheduled_events": self.unscheduled_events,
            "average_turnaround_days": self.average_turnaround_days,
            "maintenance_by_type": self.maintenance_by_type,
        }


class FleetTwin:
    def __init__(
        self,
        fleet_id: str,
        fleet_twin_id: str | None = None,
    ) -> None:
        self.fleet_twin_id: str = fleet_twin_id or str(uuid4())
        self.fleet_id: str = fleet_id
        self.aircraft_count: int = 0
        self.registered_aircraft: list[str] = []
        self.fault_statistics: FaultStatistics = FaultStatistics()
        self.life_statistics: LifeStatistics = LifeStatistics()
        self.maintenance_statistics: MaintenanceStatistics = MaintenanceStatistics()
        self.status: FleetTwinStatus = FleetTwinStatus.INACTIVE
        self.last_aggregation_time: datetime | None = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def register_aircraft(self, aircraft_sn: str) -> None:
        if aircraft_sn not in self.registered_aircraft:
            self.registered_aircraft.append(aircraft_sn)
            self.aircraft_count = len(self.registered_aircraft)
            self.updated_at = datetime.now(timezone.utc)

    def unregister_aircraft(self, aircraft_sn: str) -> None:
        if aircraft_sn in self.registered_aircraft:
            self.registered_aircraft.remove(aircraft_sn)
            self.aircraft_count = len(self.registered_aircraft)
            self.updated_at = datetime.now(timezone.utc)

    def update_statistics(self, fault_stats: FaultStatistics, life_stats: LifeStatistics, maint_stats: MaintenanceStatistics) -> None:
        self.fault_statistics = fault_stats
        self.life_statistics = life_stats
        self.maintenance_statistics = maint_stats
        self.last_aggregation_time = datetime.now(timezone.utc)
        self.status = FleetTwinStatus.ACTIVE if self.aircraft_count > 0 else FleetTwinStatus.INACTIVE
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fleet_twin_id": self.fleet_twin_id,
            "fleet_id": self.fleet_id,
            "aircraft_count": self.aircraft_count,
            "registered_aircraft": self.registered_aircraft,
            "fault_statistics": self.fault_statistics.to_dict(),
            "life_statistics": self.life_statistics.to_dict(),
            "maintenance_statistics": self.maintenance_statistics.to_dict(),
            "status": self.status.value,
            "last_aggregation_time": self.last_aggregation_time.isoformat() if self.last_aggregation_time else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }