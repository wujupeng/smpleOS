from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.domain.entities.aircraft_registration import AircraftStatus
from src.domain.services.fleet_management_service import FleetManagementService

logger = logging.getLogger(__name__)


class MaintenanceSchedule:
    def __init__(
        self,
        aircraft_sn: str,
        schedule_id: str | None = None,
    ) -> None:
        self.schedule_id: str = schedule_id or str(uuid4())
        self.aircraft_sn: str = aircraft_sn
        self.maintenance_type: str = ""
        self.scheduled_date: datetime | None = None
        self.estimated_duration_hours: float = 0.0
        self.status: str = "planned"
        self.adjustment_reason: str | None = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "aircraft_sn": self.aircraft_sn,
            "maintenance_type": self.maintenance_type,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "estimated_duration_hours": self.estimated_duration_hours,
            "status": self.status,
            "adjustment_reason": self.adjustment_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class MaintenanceSchedulingService:
    def __init__(self, fleet_management_service: FleetManagementService, event_publisher: Any | None = None) -> None:
        self._fleet_service = fleet_management_service
        self._schedules: dict[str, MaintenanceSchedule] = {}
        self._event_publisher = event_publisher

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    async def create_maintenance_schedule(self, aircraft_sn: str, maintenance_type: str, scheduled_date: datetime, estimated_duration_hours: float = 8.0) -> MaintenanceSchedule:
        aircraft = self._fleet_service.get_aircraft(aircraft_sn)
        if not aircraft:
            raise ValueError(f"Aircraft {aircraft_sn} not found")

        schedule = MaintenanceSchedule(aircraft_sn=aircraft_sn)
        schedule.maintenance_type = maintenance_type
        schedule.scheduled_date = scheduled_date
        schedule.estimated_duration_hours = estimated_duration_hours
        self._schedules[schedule.schedule_id] = schedule

        await self._fleet_service.schedule_maintenance(aircraft_sn, scheduled_date)
        await self._publish_event("operation.maintenance_schedule.created", {
            "schedule_id": schedule.schedule_id,
            "aircraft_sn": aircraft_sn,
            "maintenance_type": maintenance_type,
            "scheduled_date": scheduled_date.isoformat(),
        })
        logger.info(f"Maintenance schedule created for {aircraft_sn}: {maintenance_type}")
        return schedule

    async def adjust_schedule(self, schedule_id: str, new_date: datetime, reason: str) -> MaintenanceSchedule:
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        schedule.scheduled_date = new_date
        schedule.adjustment_reason = reason
        schedule.updated_at = datetime.now(timezone.utc)

        await self._fleet_service.schedule_maintenance(schedule.aircraft_sn, new_date)
        await self._publish_event("operation.maintenance_schedule.adjusted", {
            "schedule_id": schedule_id,
            "aircraft_sn": schedule.aircraft_sn,
            "new_date": new_date.isoformat(),
            "reason": reason,
        })
        logger.info(f"Maintenance schedule adjusted: {schedule_id}, reason: {reason}")
        return schedule

    def get_schedules_for_aircraft(self, aircraft_sn: str) -> list[MaintenanceSchedule]:
        return [s for s in self._schedules.values() if s.aircraft_sn == aircraft_sn]

    def get_upcoming_schedules(self, days: int = 30) -> list[MaintenanceSchedule]:
        now = datetime.now(timezone.utc)
        upcoming = []
        for s in self._schedules.values():
            if s.scheduled_date and (s.scheduled_date - now).days <= days and s.status == "planned":
                upcoming.append(s)
        return sorted(upcoming, key=lambda s: s.scheduled_date or now)

    def check_high_frequency_maintenance(self, aircraft_sn: str, threshold: int = 3, period_days: int = 90) -> dict[str, Any]:
        schedules = self.get_schedules_for_aircraft(aircraft_sn)
        now = datetime.now(timezone.utc)
        recent = [s for s in schedules if s.scheduled_date and (now - s.scheduled_date).days <= period_days]
        is_high_frequency = len(recent) >= threshold
        result = {
            "aircraft_sn": aircraft_sn,
            "recent_maintenance_count": len(recent),
            "period_days": period_days,
            "threshold": threshold,
            "is_high_frequency": is_high_frequency,
            "recommendation": "adjust_preventive_maintenance_plan" if is_high_frequency else None,
        }
        return result