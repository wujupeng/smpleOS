from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class AircraftStatus(str, Enum):
    ACTIVE = "active"
    GROUNDED = "grounded"
    UNDER_MAINTENANCE = "under_maintenance"
    RETIRED = "retired"


class AircraftRegistration:
    def __init__(
        self,
        aircraft_serial_number: str,
        model: str,
        registration_id: str | None = None,
    ) -> None:
        self.registration_id: str = registration_id or str(uuid4())
        self.aircraft_serial_number: str = aircraft_serial_number
        self.model: str = model
        self.registration_date: datetime = datetime.now(timezone.utc)
        self.total_flight_hours: float = 0.0
        self.next_maintenance_date: datetime | None = None
        self.status: AircraftStatus = AircraftStatus.ACTIVE
        self.fleet_id: str | None = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def add_flight_hours(self, hours: float) -> None:
        self.total_flight_hours += hours
        self.updated_at = datetime.now(timezone.utc)

    def schedule_maintenance(self, maintenance_date: datetime) -> None:
        self.next_maintenance_date = maintenance_date
        self.updated_at = datetime.now(timezone.utc)

    def set_status(self, status: AircraftStatus) -> None:
        self.status = status
        self.updated_at = datetime.now(timezone.utc)

    def assign_to_fleet(self, fleet_id: str) -> None:
        self.fleet_id = fleet_id
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "registration_id": self.registration_id,
            "aircraft_serial_number": self.aircraft_serial_number,
            "model": self.model,
            "registration_date": self.registration_date.isoformat(),
            "total_flight_hours": self.total_flight_hours,
            "next_maintenance_date": self.next_maintenance_date.isoformat() if self.next_maintenance_date else None,
            "status": self.status.value,
            "fleet_id": self.fleet_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }