from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.domain.entities.aircraft_registration import AircraftRegistration, AircraftStatus

logger = logging.getLogger(__name__)


class FleetManagementService:
    def __init__(self, event_publisher: Any | None = None) -> None:
        self._aircraft: dict[str, AircraftRegistration] = {}
        self._event_publisher = event_publisher

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    async def register_aircraft(self, aircraft_sn: str, model: str, fleet_id: str | None = None) -> AircraftRegistration:
        if aircraft_sn in self._aircraft:
            raise ValueError(f"Aircraft {aircraft_sn} already registered")
        registration = AircraftRegistration(aircraft_serial_number=aircraft_sn, model=model)
        if fleet_id:
            registration.assign_to_fleet(fleet_id)
        self._aircraft[aircraft_sn] = registration
        await self._publish_event("operation.aircraft.registered", {
            "aircraft_sn": aircraft_sn,
            "model": model,
            "fleet_id": fleet_id,
        })
        logger.info(f"Aircraft registered: {aircraft_sn}, model: {model}")
        return registration

    async def track_flight_hours(self, aircraft_sn: str, hours: float) -> AircraftRegistration:
        aircraft = self._aircraft.get(aircraft_sn)
        if not aircraft:
            raise ValueError(f"Aircraft {aircraft_sn} not found")
        aircraft.add_flight_hours(hours)
        await self._publish_event("operation.flight_hours.tracked", {
            "aircraft_sn": aircraft_sn,
            "hours_added": hours,
            "total_hours": aircraft.total_flight_hours,
        })
        return aircraft

    async def schedule_maintenance(self, aircraft_sn: str, maintenance_date: datetime) -> AircraftRegistration:
        aircraft = self._aircraft.get(aircraft_sn)
        if not aircraft:
            raise ValueError(f"Aircraft {aircraft_sn} not found")
        aircraft.schedule_maintenance(maintenance_date)
        await self._publish_event("operation.maintenance.scheduled", {
            "aircraft_sn": aircraft_sn,
            "maintenance_date": maintenance_date.isoformat(),
        })
        logger.info(f"Maintenance scheduled for {aircraft_sn}: {maintenance_date.isoformat()}")
        return aircraft

    def get_fleet_status(self, fleet_id: str | None = None) -> dict[str, Any]:
        aircraft_list = list(self._aircraft.values())
        if fleet_id:
            aircraft_list = [a for a in aircraft_list if a.fleet_id == fleet_id]
        status_counts = {}
        for a in aircraft_list:
            status_counts[a.status.value] = status_counts.get(a.status.value, 0) + 1
        return {
            "total_aircraft": len(aircraft_list),
            "status_distribution": status_counts,
            "total_flight_hours": sum(a.total_flight_hours for a in aircraft_list),
            "fleet_id": fleet_id,
        }

    def get_aircraft(self, aircraft_sn: str) -> AircraftRegistration | None:
        return self._aircraft.get(aircraft_sn)

    def list_aircraft(self, fleet_id: str | None = None) -> list[AircraftRegistration]:
        if fleet_id:
            return [a for a in self._aircraft.values() if a.fleet_id == fleet_id]
        return list(self._aircraft.values())