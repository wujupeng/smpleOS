from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .digital_twin import DigitalTwin, TwinType
from .twin_domain_service import TwinDomainService

logger = logging.getLogger(__name__)


class MaintenanceType(str, Enum):
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    IMPROVEMENT = "improvement"


class MaintenanceContent(str, Enum):
    PART_REPLACEMENT = "part_replacement"
    DEFECT_REPAIR = "defect_repair"
    SYSTEM_UPGRADE = "system_upgrade"
    INSPECTION = "inspection"
    LUBRICATION = "lubrication"


class MaintenanceResult(str, Enum):
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FOLLOW_UP_REQUIRED = "follow_up_required"


@dataclass
class MaintenanceRecord:
    record_id: str
    aircraft_sn: str
    maintenance_type: MaintenanceType
    content: MaintenanceContent
    result: MaintenanceResult
    component_id: str = ""
    component_name: str = ""
    description: str = ""
    performed_by: str = ""
    performed_at: str = ""
    flight_hours_at_maintenance: float = 0.0
    parts_replaced: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "aircraft_sn": self.aircraft_sn,
            "maintenance_type": self.maintenance_type.value,
            "content": self.content.value,
            "result": self.result.value,
            "component_id": self.component_id,
            "component_name": self.component_name,
            "description": self.description,
            "performed_by": self.performed_by,
            "performed_at": self.performed_at,
            "flight_hours_at_maintenance": self.flight_hours_at_maintenance,
            "parts_replaced": self.parts_replaced,
        }


@dataclass
class RemainingLifeEstimate:
    component_id: str
    component_name: str
    total_design_life_fh: float
    flight_hours_elapsed: float
    fatigue_damage: float
    maintenance_benefit: float
    estimated_remaining_fh: float
    confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "total_design_life_fh": self.total_design_life_fh,
            "flight_hours_elapsed": self.flight_hours_elapsed,
            "fatigue_damage": round(self.fatigue_damage, 6),
            "maintenance_benefit": round(self.maintenance_benefit, 4),
            "estimated_remaining_fh": round(self.estimated_remaining_fh, 1),
            "confidence": self.confidence,
        }


@dataclass
class MaintenancePlanItem:
    plan_item_id: str
    aircraft_sn: str
    maintenance_type: MaintenanceType
    component_id: str
    component_name: str
    description: str
    scheduled_at: str = ""
    priority: str = "normal"
    trigger_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_item_id": self.plan_item_id,
            "aircraft_sn": self.aircraft_sn,
            "maintenance_type": self.maintenance_type.value,
            "component_id": self.component_id,
            "component_name": self.component_name,
            "description": self.description,
            "scheduled_at": self.scheduled_at,
            "priority": self.priority,
            "trigger_reason": self.trigger_reason,
        }


COMPONENT_DESIGN_LIFE: dict[str, float] = {
    "wing": 60000.0,
    "fuselage": 80000.0,
    "tail": 70000.0,
    "landing_gear": 20000.0,
    "engine_mount": 30000.0,
    "hydraulic_system": 40000.0,
    "electrical_system": 50000.0,
}

REPLACEMENT_INTERVALS: dict[str, float] = {
    "landing_gear": 10000.0,
    "hydraulic_system": 15000.0,
    "engine_mount": 20000.0,
    "electrical_system": 25000.0,
}


class MaintenanceTwinService:
    def __init__(self, twin_service: TwinDomainService) -> None:
        self._twin_service = twin_service
        self._records: dict[str, list[MaintenanceRecord]] = {}
        self._life_estimates: dict[str, list[RemainingLifeEstimate]] = {}
        self._plan_items: dict[str, list[MaintenancePlanItem]] = {}
        self._record_counter: int = 0
        self._plan_counter: int = 0

    def record_maintenance(
        self,
        aircraft_sn: str,
        maintenance_type: MaintenanceType,
        content: MaintenanceContent,
        result: MaintenanceResult,
        component_id: str = "",
        component_name: str = "",
        description: str = "",
        performed_by: str = "",
        flight_hours: float = 0.0,
        parts_replaced: list[str] | None = None,
    ) -> MaintenanceRecord:
        from datetime import datetime, timezone

        twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.MAINTENANCE)
        if not twins:
            twin = self._twin_service.create_twin(
                aircraft_serial_number=aircraft_sn,
                twin_type=TwinType.MAINTENANCE,
                entity_id=aircraft_sn,
                entity_type="aircraft_maintenance",
            )
        else:
            twin = twins[0]

        self._record_counter += 1
        record = MaintenanceRecord(
            record_id=f"MR-{self._record_counter:06d}",
            aircraft_sn=aircraft_sn,
            maintenance_type=maintenance_type,
            content=content,
            result=result,
            component_id=component_id,
            component_name=component_name,
            description=description,
            performed_by=performed_by,
            performed_at=datetime.now(timezone.utc).isoformat(),
            flight_hours_at_maintenance=flight_hours,
            parts_replaced=parts_replaced or [],
        )

        if aircraft_sn not in self._records:
            self._records[aircraft_sn] = []
        self._records[aircraft_sn].append(record)

        payload: dict[str, Any] = {
            "last_maintenance_type": maintenance_type.value,
            "last_maintenance_at": record.performed_at,
            "total_maintenance_count": len(self._records[aircraft_sn]),
        }
        if result == MaintenanceResult.PART_REPLACEMENT or parts_replaced:
            payload["last_parts_replaced"] = parts_replaced or []

        twin.sync("maintenance_record", payload)

        logger.info(
            "Maintenance recorded: sn=%s type=%s component=%s",
            aircraft_sn, maintenance_type.value, component_id,
        )
        return record

    def estimate_remaining_life(
        self,
        aircraft_sn: str,
        flight_hours: float = 0.0,
        health_assessments: list[dict[str, Any]] | None = None,
    ) -> list[RemainingLifeEstimate]:
        records = self._records.get(aircraft_sn, [])
        replacement_count: dict[str, int] = {}
        for rec in records:
            if rec.content == MaintenanceContent.PART_REPLACEMENT and rec.component_id:
                replacement_count[rec.component_id] = replacement_count.get(rec.component_id, 0) + 1

        health_map: dict[str, float] = {}
        if health_assessments:
            for ha in health_assessments:
                cid = ha.get("component_id", "")
                fd = ha.get("fatigue_damage_cumulative", 0.0)
                if cid:
                    health_map[cid] = fd

        estimates: list[RemainingLifeEstimate] = []
        for comp_key, design_life in COMPONENT_DESIGN_LIFE.items():
            fatigue = health_map.get(comp_key, flight_hours / design_life if design_life > 0 else 0.0)
            replacements = replacement_count.get(comp_key, 0)
            maintenance_benefit = min(replacements * 0.3, 0.9)

            effective_damage = max(0, fatigue - maintenance_benefit)
            remaining = max(0, design_life * (1 - effective_damage) - flight_hours)

            confidence = "high" if comp_key in health_map else "medium"
            if fatigue > 0.8:
                confidence = "low"

            estimate = RemainingLifeEstimate(
                component_id=comp_key,
                component_name=comp_key.replace("_", " ").title(),
                total_design_life_fh=design_life,
                flight_hours_elapsed=flight_hours,
                fatigue_damage=effective_damage,
                maintenance_benefit=maintenance_benefit,
                estimated_remaining_fh=remaining,
                confidence=confidence,
            )
            estimates.append(estimate)

        self._life_estimates[aircraft_sn] = estimates
        return estimates

    def generate_maintenance_plan(
        self,
        aircraft_sn: str,
        flight_hours: float = 0.0,
        health_assessments: list[dict[str, Any]] | None = None,
        anomalies: list[dict[str, Any]] | None = None,
    ) -> list[MaintenancePlanItem]:
        from datetime import datetime, timedelta, timezone

        plan_items: list[MaintenancePlanItem] = []

        for comp_key, interval in REPLACEMENT_INTERVALS.items():
            hours_since_replacement = flight_hours
            records = self._records.get(aircraft_sn, [])
            for rec in reversed(records):
                if rec.component_id == comp_key and rec.content == MaintenanceContent.PART_REPLACEMENT:
                    hours_since_replacement = flight_hours - rec.flight_hours_at_maintenance
                    break

            if hours_since_replacement >= interval * 0.8:
                self._plan_counter += 1
                plan_items.append(MaintenancePlanItem(
                    plan_item_id=f"MP-{self._plan_counter:06d}",
                    aircraft_sn=aircraft_sn,
                    maintenance_type=MaintenanceType.PREVENTIVE,
                    component_id=comp_key,
                    component_name=comp_key.replace("_", " ").title(),
                    description=f"定期更换: {comp_key} (已运行 {hours_since_replacement:.0f}FH / 间隔 {interval:.0f}FH)",
                    scheduled_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                    priority="high" if hours_since_replacement >= interval else "normal",
                    trigger_reason="replacement_interval",
                ))

        if health_assessments:
            for ha in health_assessments:
                status = ha.get("health_status", "normal")
                if status in ("warning", "critical"):
                    self._plan_counter += 1
                    plan_items.append(MaintenancePlanItem(
                        plan_item_id=f"MP-{self._plan_counter:06d}",
                        aircraft_sn=aircraft_sn,
                        maintenance_type=MaintenanceType.PREVENTIVE,
                        component_id=ha.get("component_id", ""),
                        component_name=ha.get("component_name", ""),
                        description=f"视情维护: {ha.get('component_name', '')} 健康状态={status}",
                        priority="urgent" if status == "critical" else "high",
                        trigger_reason="health_assessment",
                    ))

        if anomalies:
            for anomaly in anomalies:
                self._plan_counter += 1
                plan_items.append(MaintenancePlanItem(
                    plan_item_id=f"MP-{self._plan_counter:06d}",
                    aircraft_sn=aircraft_sn,
                    maintenance_type=MaintenanceType.CORRECTIVE,
                    component_id=anomaly.get("sensor_id", ""),
                    component_name=anomaly.get("metric_name", ""),
                    description=f"纠正性维护: {anomaly.get('anomaly_type', '')}",
                    priority="urgent" if anomaly.get("severity") == "critical" else "high",
                    trigger_reason="anomaly_detected",
                ))

        self._plan_items[aircraft_sn] = plan_items
        return plan_items

    def get_maintenance_records(self, aircraft_sn: str) -> list[dict[str, Any]]:
        records = self._records.get(aircraft_sn, [])
        return [r.to_dict() for r in records]

    def get_life_estimates(self, aircraft_sn: str) -> list[dict[str, Any]]:
        estimates = self._life_estimates.get(aircraft_sn, [])
        return [e.to_dict() for e in estimates]

    def get_maintenance_plan(self, aircraft_sn: str) -> list[dict[str, Any]]:
        items = self._plan_items.get(aircraft_sn, [])
        return [p.to_dict() for p in items]