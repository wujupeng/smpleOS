from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class FlightTwinStatus(str, Enum):
    AIRBORNE = "airborne"
    GROUNDED = "grounded"
    DATA_LAGGED = "data_lagged"
    OFFLINE = "offline"


@dataclass
class FlightParameters:
    altitude_ft: float = 0.0
    airspeed_kts: float = 0.0
    heading_deg: float = 0.0
    vertical_speed_fpm: float = 0.0
    mach_number: float = 0.0
    g_force: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "altitude_ft": self.altitude_ft,
            "airspeed_kts": self.airspeed_kts,
            "heading_deg": self.heading_deg,
            "vertical_speed_fpm": self.vertical_speed_fpm,
            "mach_number": self.mach_number,
            "g_force": self.g_force,
        }


@dataclass
class StructuralLoad:
    component_id: str
    load_type: str
    load_value: float
    unit: str
    timestamp: str
    exceeds_limit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "load_type": self.load_type,
            "load_value": self.load_value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "exceeds_limit": self.exceeds_limit,
        }


@dataclass
class SystemStatus:
    system_name: str
    status: str
    health_percentage: float = 100.0
    alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_name": self.system_name,
            "status": self.status,
            "health_percentage": self.health_percentage,
            "alerts": self.alerts,
        }


class FlightTwin:
    def __init__(
        self,
        aircraft_serial_number: str,
        twin_id: str | None = None,
    ) -> None:
        self.twin_id: str = twin_id or str(uuid4())
        self.aircraft_serial_number: str = aircraft_serial_number
        self.flight_parameters: FlightParameters = FlightParameters()
        self.structural_loads: list[StructuralLoad] = []
        self.system_status: list[SystemStatus] = []
        self.last_data_time: datetime | None = None
        self.status: FlightTwinStatus = FlightTwinStatus.GROUNDED
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def update_flight_data(self, parameters: FlightParameters, loads: list[StructuralLoad] | None = None, systems: list[SystemStatus] | None = None) -> None:
        self.flight_parameters = parameters
        if loads:
            self.structural_loads = loads
        if systems:
            self.system_status = systems
        self.last_data_time = datetime.now(timezone.utc)
        self.status = FlightTwinStatus.AIRBORNE
        self.updated_at = datetime.now(timezone.utc)

    def check_data_freshness(self) -> dict[str, Any]:
        if self.last_data_time is None:
            self.status = FlightTwinStatus.OFFLINE
            return {"is_fresh": False, "lag_seconds": None, "status": "offline"}
        elapsed = (datetime.now(timezone.utc) - self.last_data_time).total_seconds()
        if elapsed < 300:
            self.status = FlightTwinStatus.AIRBORNE
            return {"is_fresh": True, "lag_seconds": elapsed, "status": "airborne"}
        elif elapsed < 3600:
            self.status = FlightTwinStatus.DATA_LAGGED
            return {"is_fresh": False, "lag_seconds": elapsed, "status": "data_lagged"}
        else:
            self.status = FlightTwinStatus.OFFLINE
            return {"is_fresh": False, "lag_seconds": elapsed, "status": "offline"}

    def get_exceeded_loads(self) -> list[StructuralLoad]:
        return [l for l in self.structural_loads if l.exceeds_limit]

    def get_system_alerts(self) -> list[dict[str, Any]]:
        alerts = []
        for s in self.system_status:
            for alert in s.alerts:
                alerts.append({"system": s.system_name, "alert": alert, "health": s.health_percentage})
        return alerts

    def mark_grounded(self) -> None:
        self.status = FlightTwinStatus.GROUNDED
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "twin_id": self.twin_id,
            "aircraft_serial_number": self.aircraft_serial_number,
            "flight_parameters": self.flight_parameters.to_dict(),
            "structural_loads": [l.to_dict() for l in self.structural_loads],
            "system_status": [s.to_dict() for s in self.system_status],
            "last_data_time": self.last_data_time.isoformat() if self.last_data_time else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }