from __future__ import annotations

import hashlib
import logging
from typing import Any

from src.domain.entities.v1.fleet_twin import FleetTwin, FaultStatistics, LifeStatistics, MaintenanceStatistics
from src.domain.entities.v1.maintenance_twin import MaintenanceTwin
from src.domain.services.v1.twin_sync_service import TwinSyncService

logger = logging.getLogger(__name__)


class FleetTwinService:
    def __init__(self, twin_sync_service: TwinSyncService, event_publisher: Any | None = None) -> None:
        self._twin_sync_service = twin_sync_service
        self._fleet_twins: dict[str, FleetTwin] = {}
        self._event_publisher = event_publisher

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def _anonymize_aircraft_sn(self, aircraft_sn: str) -> str:
        return hashlib.sha256(aircraft_sn.encode()).hexdigest()[:12]

    def get_or_create_fleet_twin(self, fleet_id: str) -> FleetTwin:
        if fleet_id not in self._fleet_twins:
            self._fleet_twins[fleet_id] = FleetTwin(fleet_id=fleet_id)
        return self._fleet_twins[fleet_id]

    async def aggregate_fleet_data(self, fleet_id: str, aircraft_sn_list: list[str] | None = None) -> FleetTwin:
        fleet_twin = self.get_or_create_fleet_twin(fleet_id)
        aircraft_list = aircraft_sn_list or fleet_twin.registered_aircraft

        available_aircraft = []
        for sn in aircraft_list:
            maint_twin = self._twin_sync_service.get_maintenance_twin(sn)
            if maint_twin:
                available_aircraft.append((sn, maint_twin))
            else:
                logger.warning(f"Aircraft {sn} data unavailable, excluding from fleet analysis")

        fault_stats = self._compute_fault_statistics(available_aircraft)
        life_stats = self._compute_life_statistics(available_aircraft)
        maint_stats = self._compute_maintenance_statistics(available_aircraft)

        fleet_twin.update_statistics(fault_stats, life_stats, maint_stats)

        for sn in aircraft_list:
            fleet_twin.register_aircraft(sn)

        await self._publish_event("fleet.twin.aggregated", {
            "fleet_id": fleet_id,
            "aircraft_count": fleet_twin.aircraft_count,
            "total_faults": fault_stats.total_faults,
            "components_due": life_stats.components_due_replacement,
        })
        logger.info(f"Fleet data aggregated for {fleet_id}: {fleet_twin.aircraft_count} aircraft")
        return fleet_twin

    def _compute_fault_statistics(self, aircraft_data: list[tuple[str, MaintenanceTwin]]) -> FaultStatistics:
        total_faults = 0
        critical_faults = 0
        faults_by_system: dict[str, int] = {}
        faults_by_aircraft: dict[str, int] = {}
        total_flight_hours = 0.0

        for sn, maint_twin in aircraft_data:
            aircraft_faults = len(maint_twin.maintenance_history)
            total_faults += aircraft_faults
            anonymized_sn = self._anonymize_aircraft_sn(sn)
            faults_by_aircraft[anonymized_sn] = aircraft_faults

            for record in maint_twin.maintenance_history:
                if record.maintenance_type == "corrective":
                    critical_faults += 1
                system = record.maintenance_type
                faults_by_system[system] = faults_by_system.get(system, 0) + 1

            for rl in maint_twin.remaining_life:
                total_flight_hours += rl.consumed_hours

        mtbf = total_flight_hours / total_faults if total_faults > 0 else 0.0
        return FaultStatistics(
            total_faults=total_faults,
            critical_faults=critical_faults,
            faults_by_system=faults_by_system,
            faults_by_aircraft=faults_by_aircraft,
            mtbf_hours=mtbf,
        )

    def _compute_life_statistics(self, aircraft_data: list[tuple[str, MaintenanceTwin]]) -> LifeStatistics:
        total_components = 0
        components_due = 0
        remaining_percentages: list[float] = []
        components_by_remaining: dict[str, int] = {"0-20%": 0, "20-40%": 0, "40-60%": 0, "60-80%": 0, "80-100%": 0}

        for sn, maint_twin in aircraft_data:
            for rl in maint_twin.remaining_life:
                total_components += 1
                remaining_percentages.append(rl.remaining_percentage)
                if rl.remaining_percentage <= 20:
                    components_due += 1
                    components_by_remaining["0-20%"] += 1
                elif rl.remaining_percentage <= 40:
                    components_by_remaining["20-40%"] += 1
                elif rl.remaining_percentage <= 60:
                    components_by_remaining["40-60%"] += 1
                elif rl.remaining_percentage <= 80:
                    components_by_remaining["60-80%"] += 1
                else:
                    components_by_remaining["80-100%"] += 1

        avg_remaining = sum(remaining_percentages) / len(remaining_percentages) if remaining_percentages else 0.0
        return LifeStatistics(
            total_components=total_components,
            components_due_replacement=components_due,
            average_remaining_life_percentage=avg_remaining,
            components_by_remaining_life=components_by_remaining,
        )

    def _compute_maintenance_statistics(self, aircraft_data: list[tuple[str, MaintenanceTwin]]) -> MaintenanceStatistics:
        total_events = 0
        scheduled = 0
        unscheduled = 0
        maint_by_type: dict[str, int] = {}
        turnaround_days: list[float] = []

        for sn, maint_twin in aircraft_data:
            for record in maint_twin.maintenance_history:
                total_events += 1
                if record.maintenance_type in ("preventive", "scheduled"):
                    scheduled += 1
                else:
                    unscheduled += 1
                maint_by_type[record.maintenance_type] = maint_by_type.get(record.maintenance_type, 0) + 1

        avg_turnaround = sum(turnaround_days) / len(turnaround_days) if turnaround_days else 0.0
        return MaintenanceStatistics(
            total_maintenance_events=total_events,
            scheduled_events=scheduled,
            unscheduled_events=unscheduled,
            average_turnaround_days=avg_turnaround,
            maintenance_by_type=maint_by_type,
        )

    async def detect_fleet_anomaly(self, fleet_id: str) -> dict[str, Any]:
        fleet_twin = self._fleet_twins.get(fleet_id)
        if not fleet_twin:
            return {"fleet_id": fleet_id, "anomalies": [], "status": "no_data"}

        anomalies = []
        if fleet_twin.fault_statistics.critical_faults > fleet_twin.aircraft_count:
            anomalies.append({
                "type": "high_critical_fault_rate",
                "description": f"Critical faults ({fleet_twin.fault_statistics.critical_faults}) exceed aircraft count ({fleet_twin.aircraft_count})",
                "severity": "high",
            })

        if fleet_twin.life_statistics.components_due_replacement > fleet_twin.life_statistics.total_components * 0.3:
            anomalies.append({
                "type": "high_component_replacement_rate",
                "description": f"{fleet_twin.life_statistics.components_due_replacement} components due replacement out of {fleet_twin.life_statistics.total_components}",
                "severity": "medium",
            })

        if fleet_twin.maintenance_statistics.unscheduled_events > fleet_twin.maintenance_statistics.scheduled_events:
            anomalies.append({
                "type": "high_unscheduled_maintenance",
                "description": f"Unscheduled events ({fleet_twin.maintenance_statistics.unscheduled_events}) exceed scheduled ({fleet_twin.maintenance_statistics.scheduled_events})",
                "severity": "medium",
            })

        result = {
            "fleet_id": fleet_id,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "status": "anomalies_detected" if anomalies else "nominal",
        }

        if anomalies:
            await self._publish_event("fleet.twin.anomaly.detected", result)
            logger.warning(f"Fleet anomaly detected for {fleet_id}: {len(anomalies)} anomalies")

        return result

    async def fleet_reliability_analysis(self, fleet_id: str) -> dict[str, Any]:
        fleet_twin = self._fleet_twins.get(fleet_id)
        if not fleet_twin:
            return {"fleet_id": fleet_id, "status": "no_data"}

        mtbf = fleet_twin.fault_statistics.mtbf_hours
        scheduled_ratio = (
            fleet_twin.maintenance_statistics.scheduled_events / fleet_twin.maintenance_statistics.total_maintenance_events
            if fleet_twin.maintenance_statistics.total_maintenance_events > 0
            else 0.0
        )
        avg_life = fleet_twin.life_statistics.average_remaining_life_percentage

        reliability_score = (mtbf / 1000.0 * 0.4 + scheduled_ratio * 0.3 + avg_life / 100.0 * 0.3) * 100
        reliability_score = min(max(reliability_score, 0), 100)

        return {
            "fleet_id": fleet_id,
            "mtbf_hours": mtbf,
            "scheduled_maintenance_ratio": round(scheduled_ratio, 3),
            "average_remaining_life_percentage": round(avg_life, 1),
            "reliability_score": round(reliability_score, 1),
            "assessment": "excellent" if reliability_score >= 80 else "good" if reliability_score >= 60 else "needs_attention" if reliability_score >= 40 else "critical",
        }

    async def fleet_maintenance_optimization(self, fleet_id: str) -> dict[str, Any]:
        fleet_twin = self._fleet_twins.get(fleet_id)
        if not fleet_twin:
            return {"fleet_id": fleet_id, "status": "no_data"}

        recommendations = []
        if fleet_twin.maintenance_statistics.unscheduled_events > fleet_twin.maintenance_statistics.scheduled_events:
            recommendations.append({
                "type": "increase_preventive_maintenance",
                "reason": "High unscheduled maintenance ratio",
                "priority": "high",
            })

        if fleet_twin.life_statistics.components_due_replacement > 0:
            recommendations.append({
                "type": "schedule_component_replacements",
                "reason": f"{fleet_twin.life_statistics.components_due_replacement} components due for replacement",
                "priority": "high",
            })

        if fleet_twin.fault_statistics.mtbf_hours < 500:
            recommendations.append({
                "type": "review_maintenance_program",
                "reason": f"Low MTBF: {fleet_twin.fault_statistics.mtbf_hours:.0f} hours",
                "priority": "medium",
            })

        return {
            "fleet_id": fleet_id,
            "recommendations": recommendations,
            "recommendation_count": len(recommendations),
        }

    async def fleet_configuration_comparison(self, fleet_id: str) -> dict[str, Any]:
        fleet_twin = self._fleet_twins.get(fleet_id)
        if not fleet_twin:
            return {"fleet_id": fleet_id, "status": "no_data"}

        aircraft_configs: dict[str, list[str]] = {}
        for sn in fleet_twin.registered_aircraft:
            design_twin = self._twin_sync_service.get_design_twin(sn)
            if design_twin:
                config_key = f"v{design_twin.model_version}"
                aircraft_configs.setdefault(config_key, []).append(sn)

        return {
            "fleet_id": fleet_id,
            "configuration_groups": aircraft_configs,
            "unique_configurations": len(aircraft_configs),
            "is_uniform": len(aircraft_configs) <= 1,
        }

    async def predictive_maintenance(self, fleet_id: str, aircraft_sn: str) -> dict[str, Any]:
        maint_twin = self._twin_sync_service.get_maintenance_twin(aircraft_sn)
        if not maint_twin:
            return {"fleet_id": fleet_id, "aircraft_sn": aircraft_sn, "status": "no_data"}

        due_components = maint_twin.get_components_due_for_replacement(threshold_percentage=30.0)
        predictions = []
        for rl in due_components:
            degradation_rate = rl.consumed_hours / max(rl.total_life_hours, 1)
            remaining_days = (rl.remaining_hours / max(degradation_rate * 24, 0.01)) if degradation_rate > 0 else float('inf')
            predictions.append({
                "component_id": rl.component_id,
                "component_name": rl.component_name,
                "remaining_hours": rl.remaining_hours,
                "remaining_percentage": rl.remaining_percentage,
                "estimated_days_until_due": min(remaining_days, 365),
                "priority": "high" if rl.remaining_percentage <= 10 else "medium",
            })

        return {
            "fleet_id": fleet_id,
            "aircraft_sn": aircraft_sn,
            "predictions": predictions,
            "prediction_count": len(predictions),
        }

    def get_fleet_twin(self, fleet_id: str) -> FleetTwin | None:
        return self._fleet_twins.get(fleet_id)