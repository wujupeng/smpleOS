from __future__ import annotations

import logging
from typing import Any

from src.domain.services.fleet_management_service import FleetManagementService

logger = logging.getLogger(__name__)


class OperationAnalyticsService:
    def __init__(self, fleet_management_service: FleetManagementService, event_publisher: Any | None = None) -> None:
        self._fleet_service = fleet_management_service
        self._event_publisher = event_publisher

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def calculate_utilization_rate(self, fleet_id: str | None = None, period_days: int = 30) -> dict[str, Any]:
        aircraft_list = self._fleet_service.list_aircraft(fleet_id)
        if not aircraft_list:
            return {"fleet_id": fleet_id, "utilization_rate": 0.0, "period_days": period_days}

        total_available_hours = len(aircraft_list) * period_days * 24
        total_flight_hours = sum(a.total_flight_hours for a in aircraft_list)
        utilization_rate = (total_flight_hours / total_available_hours * 100) if total_available_hours > 0 else 0.0
        utilization_rate = min(utilization_rate, 100.0)

        return {
            "fleet_id": fleet_id,
            "utilization_rate": round(utilization_rate, 2),
            "period_days": period_days,
            "total_flight_hours": total_flight_hours,
            "total_available_hours": total_available_hours,
            "aircraft_count": len(aircraft_list),
        }

    def calculate_dispatch_reliability(self, fleet_id: str | None = None, period_days: int = 30) -> dict[str, Any]:
        aircraft_list = self._fleet_service.list_aircraft(fleet_id)
        if not aircraft_list:
            return {"fleet_id": fleet_id, "dispatch_reliability": 0.0, "period_days": period_days}

        active_count = sum(1 for a in aircraft_list if a.status.value == "active")
        total_scheduled_departures = len(aircraft_list) * period_days
        dispatch_reliability = (active_count / len(aircraft_list) * 100) if aircraft_list else 0.0

        return {
            "fleet_id": fleet_id,
            "dispatch_reliability": round(dispatch_reliability, 2),
            "period_days": period_days,
            "active_aircraft": active_count,
            "total_aircraft": len(aircraft_list),
            "total_scheduled_departures": total_scheduled_departures,
        }

    def calculate_maintenance_cost(self, fleet_id: str | None = None, period_days: int = 30) -> dict[str, Any]:
        aircraft_list = self._fleet_service.list_aircraft(fleet_id)
        if not aircraft_list:
            return {"fleet_id": fleet_id, "total_cost": 0.0, "period_days": period_days}

        under_maintenance = sum(1 for a in aircraft_list if a.status.value == "under_maintenance")
        estimated_cost_per_aircraft_per_day = 5000.0
        scheduled_cost = under_maintenance * period_days * estimated_cost_per_aircraft_per_day
        unscheduled_cost = scheduled_cost * 0.3
        total_cost = scheduled_cost + unscheduled_cost

        return {
            "fleet_id": fleet_id,
            "total_cost": round(total_cost, 2),
            "scheduled_cost": round(scheduled_cost, 2),
            "unscheduled_cost": round(unscheduled_cost, 2),
            "period_days": period_days,
            "aircraft_under_maintenance": under_maintenance,
        }

    async def generate_operation_report(self, fleet_id: str | None = None, period_days: int = 30) -> dict[str, Any]:
        utilization = self.calculate_utilization_rate(fleet_id, period_days)
        dispatch = self.calculate_dispatch_reliability(fleet_id, period_days)
        cost = self.calculate_maintenance_cost(fleet_id, period_days)
        fleet_status = self._fleet_service.get_fleet_status(fleet_id)

        report = {
            "report_type": "operation_analytics",
            "fleet_id": fleet_id,
            "period_days": period_days,
            "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "fleet_overview": fleet_status,
            "utilization": utilization,
            "dispatch_reliability": dispatch,
            "maintenance_cost": cost,
        }

        await self._publish_event("operation.analytics.report_generated", report)
        logger.info(f"Operation report generated for fleet {fleet_id}")
        return report