from __future__ import annotations

import logging
from typing import Any

from src.domain.entities.v1.design_twin import DesignTwin, DesignParameter
from src.domain.entities.v1.maintenance_twin import MaintenanceTwin, HealthIndicator
from src.domain.services.v1.twin_sync_service import TwinSyncService

logger = logging.getLogger(__name__)


class TwinFeedbackService:
    def __init__(self, twin_sync_service: TwinSyncService, event_publisher: Any | None = None) -> None:
        self._twin_sync_service = twin_sync_service
        self._event_publisher = event_publisher

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    async def feedback_flight_to_design(self, aircraft_sn: str) -> dict[str, Any]:
        flight_twin = self._twin_sync_service.get_flight_twin(aircraft_sn)
        design_twin = self._twin_sync_service.get_design_twin(aircraft_sn)
        if not flight_twin or not design_twin:
            return {"aircraft_sn": aircraft_sn, "feedback_type": "flight_to_design", "status": "no_twins_available"}

        exceeded_loads = flight_twin.get_exceeded_loads()
        feedback_items = []
        for load in exceeded_loads:
            design_param = design_twin.get_parameter(load.component_id)
            if design_param:
                feedback_items.append({
                    "component_id": load.component_id,
                    "load_type": load.load_type,
                    "actual_load": load.load_value,
                    "design_limit": design_param.value,
                    "exceeds_by": load.load_value - design_param.value,
                    "unit": load.unit,
                })

        result = {
            "aircraft_sn": aircraft_sn,
            "feedback_type": "flight_to_design",
            "exceeded_loads_count": len(exceeded_loads),
            "feedback_items": feedback_items,
            "status": "action_required" if feedback_items else "nominal",
        }
        await self._publish_event("twin.feedback.flight_to_design", result)
        logger.info(f"Flight-to-design feedback for {aircraft_sn}: {len(feedback_items)} items")
        return result

    async def feedback_manufacturing_to_design(self, aircraft_sn: str) -> dict[str, Any]:
        mfg_twin = self._twin_sync_service.get_manufacturing_twin(aircraft_sn)
        design_twin = self._twin_sync_service.get_design_twin(aircraft_sn)
        if not mfg_twin or not design_twin:
            return {"aircraft_sn": aircraft_sn, "feedback_type": "manufacturing_to_design", "status": "no_twins_available"}

        out_of_tol = mfg_twin.get_out_of_tolerance_deviations()
        feedback_items = []
        for dev in out_of_tol:
            feedback_items.append({
                "parameter_name": dev.parameter_name,
                "design_value": dev.design_value,
                "actual_value": dev.actual_value,
                "deviation": dev.deviation,
                "tolerance": dev.tolerance,
                "exceeds_tolerance_by": dev.deviation - dev.tolerance,
                "unit": dev.unit,
            })

        result = {
            "aircraft_sn": aircraft_sn,
            "feedback_type": "manufacturing_to_design",
            "out_of_tolerance_count": len(out_of_tol),
            "feedback_items": feedback_items,
            "status": "action_required" if feedback_items else "nominal",
        }
        await self._publish_event("twin.feedback.mfg_to_design", result)
        logger.info(f"Mfg-to-design feedback for {aircraft_sn}: {len(feedback_items)} items")
        return result

    async def feedback_flight_to_maintenance(self, aircraft_sn: str) -> dict[str, Any]:
        flight_twin = self._twin_sync_service.get_flight_twin(aircraft_sn)
        maint_twin = self._twin_sync_service.get_maintenance_twin(aircraft_sn)
        if not flight_twin or not maint_twin:
            return {"aircraft_sn": aircraft_sn, "feedback_type": "flight_to_maintenance", "status": "no_twins_available"}

        exceeded_loads = flight_twin.get_exceeded_loads()
        system_alerts = flight_twin.get_system_alerts()
        recommendations = []

        for load in exceeded_loads:
            recommendations.append({
                "type": "increase_inspection_frequency",
                "component_id": load.component_id,
                "reason": f"Structural load exceeded limit: {load.load_value} {load.unit}",
                "suggested_interval": "reduced",
            })

        for alert in system_alerts:
            if alert["health"] < 80:
                recommendations.append({
                    "type": "increase_inspection_frequency",
                    "system": alert["system"],
                    "reason": f"System health degraded: {alert['health']}%, alert: {alert['alert']}",
                    "suggested_interval": "reduced",
                })

        result = {
            "aircraft_sn": aircraft_sn,
            "feedback_type": "flight_to_maintenance",
            "exceeded_loads_count": len(exceeded_loads),
            "system_alerts_count": len(system_alerts),
            "recommendations": recommendations,
            "status": "action_required" if recommendations else "nominal",
        }
        await self._publish_event("twin.feedback.flight_to_maintenance", result)
        logger.info(f"Flight-to-maintenance feedback for {aircraft_sn}: {len(recommendations)} recommendations")
        return result

    async def feedback_maintenance_to_manufacturing(self, aircraft_sn: str) -> dict[str, Any]:
        maint_twin = self._twin_sync_service.get_maintenance_twin(aircraft_sn)
        mfg_twin = self._twin_sync_service.get_manufacturing_twin(aircraft_sn)
        if not maint_twin or not mfg_twin:
            return {"aircraft_sn": aircraft_sn, "feedback_type": "maintenance_to_manufacturing", "status": "no_twins_available"}

        frequent_repairs = self._detect_frequent_repairs(maint_twin)
        mfg_deviations = mfg_twin.get_out_of_tolerance_deviations() if mfg_twin else []
        feedback_items = []

        for repair in frequent_repairs:
            matching_devs = [d for d in mfg_deviations if d.parameter_name == repair["component_id"]]
            feedback_items.append({
                "component_id": repair["component_id"],
                "repair_count": repair["count"],
                "manufacturing_deviation": matching_devs[0].to_dict() if matching_devs else None,
                "recommendation": "review_manufacturing_process" if matching_devs else "monitor",
            })

        result = {
            "aircraft_sn": aircraft_sn,
            "feedback_type": "maintenance_to_manufacturing",
            "frequent_repairs_count": len(frequent_repairs),
            "feedback_items": feedback_items,
            "status": "action_required" if any(f["recommendation"] == "review_manufacturing_process" for f in feedback_items) else "nominal",
        }
        await self._publish_event("twin.feedback.maintenance_to_mfg", result)
        logger.info(f"Maintenance-to-mfg feedback for {aircraft_sn}: {len(feedback_items)} items")
        return result

    def _detect_frequent_repairs(self, maint_twin: MaintenanceTwin, threshold: int = 3) -> list[dict[str, Any]]:
        component_repair_counts: dict[str, int] = {}
        for replacement in maint_twin.component_replacements:
            component_repair_counts[replacement.component_id] = component_repair_counts.get(replacement.component_id, 0) + 1
        return [{"component_id": cid, "count": count} for cid, count in component_repair_counts.items() if count >= threshold]