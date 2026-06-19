from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.domain.services.fleet_management_service import FleetManagementService

logger = logging.getLogger(__name__)


class FlightDataMonitoringService:
    def __init__(self, fleet_management_service: FleetManagementService, event_publisher: Any | None = None) -> None:
        self._fleet_service = fleet_management_service
        self._flight_data: dict[str, list[dict[str, Any]]] = {}
        self._alerts: dict[str, list[dict[str, Any]]] = {}
        self._event_publisher = event_publisher

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    async def ingest_flight_data(self, aircraft_sn: str, data: dict[str, Any]) -> dict[str, Any]:
        aircraft = self._fleet_service.get_aircraft(aircraft_sn)
        if not aircraft:
            raise ValueError(f"Aircraft {aircraft_sn} not found")

        data_point = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "aircraft_sn": aircraft_sn,
            **data,
        }
        self._flight_data.setdefault(aircraft_sn, []).append(data_point)

        if "flight_hours" in data:
            await self._fleet_service.track_flight_hours(aircraft_sn, data["flight_hours"])

        anomalies = self._check_anomalies(aircraft_sn, data_point)
        if anomalies:
            self._alerts.setdefault(aircraft_sn, []).extend(anomalies)
            await self._publish_event("operation.flight.anomaly_detected", {
                "aircraft_sn": aircraft_sn,
                "anomalies": anomalies,
            })
            logger.warning(f"Flight anomaly detected for {aircraft_sn}: {len(anomalies)} anomalies")

        return {
            "aircraft_sn": aircraft_sn,
            "ingested": True,
            "anomalies_detected": len(anomalies),
            "data_points_stored": len(self._flight_data.get(aircraft_sn, [])),
        }

    def monitor_flight_status(self, aircraft_sn: str) -> dict[str, Any]:
        aircraft = self._fleet_service.get_aircraft(aircraft_sn)
        if not aircraft:
            return {"aircraft_sn": aircraft_sn, "status": "not_found"}

        data_points = self._flight_data.get(aircraft_sn, [])
        alerts = self._alerts.get(aircraft_sn, [])
        latest_data = data_points[-1] if data_points else None

        return {
            "aircraft_sn": aircraft_sn,
            "aircraft_status": aircraft.status.value,
            "total_flight_hours": aircraft.total_flight_hours,
            "data_points_count": len(data_points),
            "active_alerts": len(alerts),
            "latest_data": latest_data,
        }

    def _check_anomalies(self, aircraft_sn: str, data_point: dict[str, Any]) -> list[dict[str, Any]]:
        anomalies = []
        if data_point.get("altitude_ft", 0) > 51000:
            anomalies.append({
                "type": "altitude_exceeded",
                "parameter": "altitude_ft",
                "value": data_point["altitude_ft"],
                "threshold": 51000,
                "severity": "high",
            })
        if data_point.get("g_force", 1.0) > 3.5:
            anomalies.append({
                "type": "g_force_exceeded",
                "parameter": "g_force",
                "value": data_point["g_force"],
                "threshold": 3.5,
                "severity": "high",
            })
        if data_point.get("engine_temp_c", 0) > 1050:
            anomalies.append({
                "type": "engine_temp_exceeded",
                "parameter": "engine_temp_c",
                "value": data_point["engine_temp_c"],
                "threshold": 1050,
                "severity": "medium",
            })
        return anomalies

    def get_alerts(self, aircraft_sn: str) -> list[dict[str, Any]]:
        return self._alerts.get(aircraft_sn, [])

    def get_flight_data(self, aircraft_sn: str, limit: int = 100) -> list[dict[str, Any]]:
        data = self._flight_data.get(aircraft_sn, [])
        return data[-limit:]