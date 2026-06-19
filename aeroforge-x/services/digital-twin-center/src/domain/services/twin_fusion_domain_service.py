from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from ..entities.unified_twin import (
    ConflictResolution,
    CrossTwinInsight,
    FusionRecord,
    FusionStatus,
    InsightCategory,
    InsightSeverity,
    TwinDataConflict,
    TwinReference,
    UnifiedTwin,
)

logger = logging.getLogger(__name__)


class TwinFusionDomainService:
    def __init__(self) -> None:
        self._twins: dict[str, UnifiedTwin] = {}
        self._sn_index: dict[str, str] = {}

    def create_unified_twin(
        self,
        aircraft_serial_number: str,
        tenant_id: str,
        project_id: str,
        design_twin_id: str | None = None,
        manufacturing_twin_id: str | None = None,
        flight_twin_id: str | None = None,
        maintenance_twin_id: str | None = None,
    ) -> UnifiedTwin:
        twin = UnifiedTwin(
            aircraft_serial_number=aircraft_serial_number,
            tenant_id=tenant_id,
            project_id=project_id,
        )

        if design_twin_id:
            twin.set_twin_reference("design", TwinReference(
                twin_id=design_twin_id, twin_type="design", last_sync=datetime.now(timezone.utc),
            ))
        if manufacturing_twin_id:
            twin.set_twin_reference("manufacturing", TwinReference(
                twin_id=manufacturing_twin_id, twin_type="manufacturing", last_sync=datetime.now(timezone.utc),
            ))
        if flight_twin_id:
            twin.set_twin_reference("flight", TwinReference(
                twin_id=flight_twin_id, twin_type="flight", last_sync=datetime.now(timezone.utc),
            ))
        if maintenance_twin_id:
            twin.set_twin_reference("maintenance", TwinReference(
                twin_id=maintenance_twin_id, twin_type="maintenance", last_sync=datetime.now(timezone.utc),
            ))

        twin.update_fusion_status()

        self._twins[twin.id] = twin
        self._sn_index[aircraft_serial_number] = twin.id

        twin.add_domain_event(DomainEvent(
            event_type="twin.unified_created",
            aggregate_id=twin.id,
            payload={
                "aircraft_sn": aircraft_serial_number,
                "tenant_id": tenant_id,
                "active_twins": twin.get_active_twin_count(),
                "fusion_status": twin.fusion_status.value,
            },
        ))

        logger.info("Unified twin created: sn=%s status=%s", aircraft_serial_number, twin.fusion_status.value)
        return twin

    def fuse_twin_data(
        self,
        aircraft_sn: str,
        design_data: dict[str, Any] | None = None,
        manufacturing_data: dict[str, Any] | None = None,
        flight_data: dict[str, Any] | None = None,
        maintenance_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        twin = self._get_by_sn(aircraft_sn)
        if twin is None:
            return {"error": "Unified twin not found"}

        start_time = datetime.now(timezone.utc)
        new_version = twin.fusion_version + 1

        design_hash = self._compute_data_hash(design_data) if design_data else ""
        mfg_hash = self._compute_data_hash(manufacturing_data) if manufacturing_data else ""
        flight_hash = self._compute_data_hash(flight_data) if flight_data else ""
        maint_hash = self._compute_data_hash(maintenance_data) if maintenance_data else ""

        insights = self._generate_cross_insights(
            twin, design_data or {}, manufacturing_data or {},
            flight_data or {}, maintenance_data or {},
        )
        for insight in insights:
            twin.add_insight(insight)

        conflicts = self._detect_conflicts(
            twin, design_data or {}, manufacturing_data or {},
            flight_data or {}, maintenance_data or {},
        )
        for conflict in conflicts:
            twin.add_conflict(conflict)

        resolved = self._auto_resolve_conflicts(twin.conflicts)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        record = FusionRecord(
            record_id=f"FR-{secrets.token_hex(4)}",
            fusion_version=new_version,
            design_data_hash=design_hash,
            manufacturing_data_hash=mfg_hash,
            flight_data_hash=flight_hash,
            maintenance_data_hash=maint_hash,
            insights_generated=len(insights),
            conflicts_detected=len(conflicts),
            conflicts_resolved=resolved,
            duration_ms=round(duration, 1),
        )
        twin.add_fusion_record(record)
        twin.update_fusion_status()

        twin.add_domain_event(DomainEvent(
            event_type="twin.fusion_completed",
            aggregate_id=twin.id,
            payload={
                "aircraft_sn": aircraft_sn,
                "fusion_version": new_version,
                "insights": len(insights),
                "conflicts": len(conflicts),
                "status": twin.fusion_status.value,
            },
        ))

        logger.info(
            "Twin fusion completed: sn=%s v=%d insights=%d conflicts=%d",
            aircraft_sn, new_version, len(insights), len(conflicts),
        )

        return {
            "fusion_version": new_version,
            "fusion_status": twin.fusion_status.value,
            "insights_generated": len(insights),
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": resolved,
            "duration_ms": round(duration, 1),
            "insights": [i.to_dict() for i in insights],
            "conflicts": [c.to_dict() for c in conflicts],
        }

    def detect_cross_twin_anomaly(self, aircraft_sn: str) -> list[dict[str, Any]]:
        twin = self._get_by_sn(aircraft_sn)
        if twin is None:
            return []

        anomalies = []
        for insight in twin.cross_twin_insights:
            if insight.severity in (InsightSeverity.WARNING, InsightSeverity.CRITICAL):
                anomalies.append(insight.to_dict())

        return anomalies

    def reconcile_conflicts(
        self,
        aircraft_sn: str,
        conflict_id: str,
        resolution: ConflictResolution,
        resolved_by: str = "",
    ) -> dict[str, Any]:
        twin = self._get_by_sn(aircraft_sn)
        if twin is None:
            return {"error": "Unified twin not found"}

        for conflict in twin.conflicts:
            if conflict.conflict_id == conflict_id:
                conflict.resolution = resolution
                conflict.resolved_by = resolved_by
                conflict.resolved_at = datetime.now(timezone.utc)

                if resolution == ConflictResolution.MEASURED_WINS:
                    conflict.resolved_value = conflict.measured_value
                elif resolution == ConflictResolution.DESIGN_WINS:
                    conflict.resolved_value = conflict.design_value
                elif resolution == ConflictResolution.INFERRED_WINS:
                    conflict.resolved_value = conflict.inferred_value

                logger.info("Conflict resolved: %s -> %s by %s", conflict_id, resolution.value, resolved_by)
                return {"resolved": True, "conflict_id": conflict_id, "resolution": resolution.value}

        return {"resolved": False, "reason": "Conflict not found"}

    def propagate_insight(self, aircraft_sn: str, insight_id: str) -> dict[str, Any]:
        twin = self._get_by_sn(aircraft_sn)
        if twin is None:
            return {"error": "Unified twin not found"}

        for insight in twin.cross_twin_insights:
            if insight.insight_id == insight_id:
                insight.acknowledged = True
                event_type = f"twin.insight.propagated.{insight.category.value}"
                twin.add_domain_event(DomainEvent(
                    event_type=event_type,
                    aggregate_id=twin.id,
                    payload={
                        "insight_id": insight_id,
                        "source_twin": insight.source_twin,
                        "target_twin": insight.target_twin,
                        "recommendation": insight.recommendation,
                    },
                ))
                logger.info("Insight propagated: %s from %s to %s", insight_id, insight.source_twin, insight.target_twin)
                return {"propagated": True, "insight_id": insight_id}

        return {"propagated": False, "reason": "Insight not found"}

    def get_unified_twin(self, aircraft_sn: str) -> UnifiedTwin | None:
        return self._get_by_sn(aircraft_sn)

    def get_insights(self, aircraft_sn: str, severity: InsightSeverity | None = None) -> list[dict[str, Any]]:
        twin = self._get_by_sn(aircraft_sn)
        if twin is None:
            return []
        insights = twin.cross_twin_insights
        if severity:
            insights = [i for i in insights if i.severity == severity]
        return [i.to_dict() for i in insights]

    def _get_by_sn(self, aircraft_sn: str) -> UnifiedTwin | None:
        twin_id = self._sn_index.get(aircraft_sn)
        if twin_id:
            return self._twins.get(twin_id)
        return None

    def _generate_cross_insights(
        self,
        twin: UnifiedTwin,
        design_data: dict[str, Any],
        manufacturing_data: dict[str, Any],
        flight_data: dict[str, Any],
        maintenance_data: dict[str, Any],
    ) -> list[CrossTwinInsight]:
        insights: list[CrossTwinInsight] = []

        design_params = design_data.get("parameters", {})
        mfg_deviations = manufacturing_data.get("deviations", {})
        flight_loads = flight_data.get("loads", {})
        maint_health = maintenance_data.get("health_indicators", {})

        if design_params and mfg_deviations:
            for param_name, design_val in design_params.items():
                if param_name in mfg_deviations:
                    deviation = mfg_deviations[param_name]
                    if isinstance(deviation, (int, float)) and isinstance(design_val, (int, float)):
                        if design_val != 0 and abs(deviation / design_val) > 0.05:
                            insights.append(CrossTwinInsight(
                                insight_id=f"INS-{secrets.token_hex(4)}",
                                category=InsightCategory.DESIGN_DEVIATION,
                                severity=InsightSeverity.WARNING if abs(deviation / design_val) > 0.1 else InsightSeverity.INFO,
                                source_twin="manufacturing",
                                target_twin="design",
                                description=f"Manufacturing deviation for {param_name}: {deviation:.4f} vs design {design_val:.4f} ({abs(deviation/design_val)*100:.1f}%)",
                                evidence={"parameter": param_name, "design_value": design_val, "deviation": deviation},
                                recommendation="Review design tolerances or improve manufacturing process",
                            ))

        if mfg_deviations and flight_loads:
            max_load = flight_loads.get("max_load_factor", 0)
            if max_load > 0:
                critical_deviation = any(
                    abs(v) > 0.1 for v in mfg_deviations.values() if isinstance(v, (int, float))
                )
                if critical_deviation and max_load > 3.0:
                    insights.append(CrossTwinInsight(
                        insight_id=f"INS-{secrets.token_hex(4)}",
                        category=InsightCategory.MANUFACTURING_IMPACT,
                        severity=InsightSeverity.CRITICAL,
                        source_twin="manufacturing",
                        target_twin="flight",
                        description="Critical manufacturing deviations detected under high flight loads",
                        evidence={"max_load_factor": max_load, "deviation_count": len(mfg_deviations)},
                        recommendation="Conduct additional structural inspection before next flight",
                    ))

        if flight_loads and maint_health:
            degradation_rate = maint_health.get("degradation_rate", 0)
            avg_load = flight_loads.get("avg_load_factor", 0)
            if degradation_rate > 0.05 and avg_load > 2.5:
                insights.append(CrossTwinInsight(
                    insight_id=f"INS-{secrets.token_hex(4)}",
                    category=InsightCategory.MAINTENANCE_RECOMMENDATION,
                    severity=InsightSeverity.WARNING,
                    source_twin="flight",
                    target_twin="maintenance",
                    description=f"High flight loads (avg {avg_load:.1f}g) accelerating degradation (rate {degradation_rate:.3f})",
                    evidence={"avg_load": avg_load, "degradation_rate": degradation_rate},
                    recommendation="Increase maintenance inspection frequency",
                ))

        return insights

    def _detect_conflicts(
        self,
        twin: UnifiedTwin,
        design_data: dict[str, Any],
        manufacturing_data: dict[str, Any],
        flight_data: dict[str, Any],
        maintenance_data: dict[str, Any],
    ) -> list[TwinDataConflict]:
        conflicts: list[TwinDataConflict] = []

        design_params = design_data.get("parameters", {})
        flight_measurements = flight_data.get("measurements", {})

        for param_name, design_val in design_params.items():
            if param_name in flight_measurements:
                measured_val = flight_measurements[param_name]
                if isinstance(design_val, (int, float)) and isinstance(measured_val, (int, float)):
                    if design_val != 0:
                        deviation = abs((measured_val - design_val) / design_val) * 100
                        if deviation > 10:
                            conflicts.append(TwinDataConflict(
                                conflict_id=f"CF-{secrets.token_hex(4)}",
                                parameter=param_name,
                                design_value=design_val,
                                measured_value=measured_val,
                                deviation_percent=round(deviation, 2),
                            ))

        return conflicts

    def _auto_resolve_conflicts(self, conflicts: list[TwinDataConflict]) -> int:
        resolved = 0
        for conflict in conflicts:
            if conflict.resolution != ConflictResolution.PENDING:
                continue
            if conflict.measured_value is not None and conflict.design_value is not None:
                conflict.resolution = ConflictResolution.MEASURED_WINS
                conflict.resolved_value = conflict.measured_value
                resolved += 1
        return resolved

    def _compute_data_hash(self, data: dict[str, Any]) -> str:
        payload = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]