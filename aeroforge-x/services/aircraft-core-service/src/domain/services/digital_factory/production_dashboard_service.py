"""AeroForge-X v6.0 ProductionDashboardService

Provides real-time production monitoring dashboard: OEE computation,
AGV fleet monitoring, bottleneck detection, and delivery impact assessment.
REQ-FACTORY-013~018
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EquipmentOEE:
    equipment_id: str
    availability: float = 0.0
    performance: float = 0.0
    quality: float = 0.0
    oee: float = 0.0

    def to_dict(self) -> dict:
        return {
            "equipment_id": self.equipment_id,
            "availability": self.availability,
            "performance": self.performance,
            "quality": self.quality,
            "oee": self.oee,
        }


@dataclass
class AGVDetail:
    agv_id: str
    location: str = ""
    task_status: str = "Idle"
    battery_level: float = 100.0
    collision_avoidance_status: str = "Clear"

    def to_dict(self) -> dict:
        return {
            "agv_id": self.agv_id,
            "location": self.location,
            "task_status": self.task_status,
            "battery_level": self.battery_level,
            "collision_avoidance_status": self.collision_avoidance_status,
        }


@dataclass
class AGVFleetStatus:
    total_agvs: int
    active_agvs: int
    idle_agvs: int
    low_battery_agvs: int
    details: list[AGVDetail] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_agvs": self.total_agvs,
            "active_agvs": self.active_agvs,
            "idle_agvs": self.idle_agvs,
            "low_battery_agvs": self.low_battery_agvs,
            "details": [d.to_dict() for d in self.details],
        }


@dataclass
class BottleneckDetection:
    constraint_operation_id: str
    utilization_rate: float
    suggested_capacity_adjustment: str

    def to_dict(self) -> dict:
        return {
            "constraint_operation_id": self.constraint_operation_id,
            "utilization_rate": self.utilization_rate,
            "suggested_capacity_adjustment": self.suggested_capacity_adjustment,
        }


@dataclass
class DeliveryImpactAssessment:
    bottleneck: BottleneckDetection
    delivery_delay_days: float
    mitigation_recommendation: str

    def to_dict(self) -> dict:
        return {
            "bottleneck": self.bottleneck.to_dict(),
            "delivery_delay_days": self.delivery_delay_days,
            "mitigation_recommendation": self.mitigation_recommendation,
        }


class ProductionDashboardService:

    OEE_LOW_THRESHOLD = 0.65
    UTILIZATION_BOTTLENECK_THRESHOLD = 0.90

    def __init__(self) -> None:
        self._oee_data: dict[str, EquipmentOEE] = {}
        self._agv_data: dict[str, AGVDetail] = {}
        self._operation_utilization: dict[str, float] = {}

    def getEquipmentOEE(self, equipment_id: str) -> EquipmentOEE:
        if equipment_id in self._oee_data:
            return self._oee_data[equipment_id]
        return EquipmentOEE(equipment_id=equipment_id)

    def computeOEE(
        self,
        equipment_id: str,
        planned_time: float,
        run_time: float,
        ideal_cycle_time: float,
        actual_cycle_time: float,
        total_pieces: float,
        good_pieces: float,
    ) -> EquipmentOEE:
        availability = run_time / planned_time if planned_time > 0 else 0
        performance = (ideal_cycle_time * total_pieces) / run_time if run_time > 0 else 0
        quality = good_pieces / total_pieces if total_pieces > 0 else 0
        oee = availability * performance * quality

        result = EquipmentOEE(
            equipment_id=equipment_id,
            availability=round(availability, 4),
            performance=round(min(performance, 1.0), 4),
            quality=round(quality, 4),
            oee=round(oee, 4),
        )
        self._oee_data[equipment_id] = result
        return result

    def getAGVFleetStatus(self) -> AGVFleetStatus:
        details = list(self._agv_data.values())
        active = sum(1 for d in details if d.task_status != "Idle")
        idle = sum(1 for d in details if d.task_status == "Idle")
        low_battery = sum(1 for d in details if d.battery_level < 20)

        return AGVFleetStatus(
            total_agvs=len(details),
            active_agvs=active,
            idle_agvs=idle,
            low_battery_agvs=low_battery,
            details=details,
        )

    def updateAGVStatus(self, agv: AGVDetail) -> None:
        self._agv_data[agv.agv_id] = agv

    def detectBottleneck(self, line_id: str) -> Optional[BottleneckDetection]:
        if not self._operation_utilization:
            return None

        max_op = max(self._operation_utilization, key=self._operation_utilization.get)
        max_util = self._operation_utilization[max_op]

        if max_util >= self.UTILIZATION_BOTTLENECK_THRESHOLD:
            suggestion = "Add parallel station" if max_util > 0.95 else "Optimize cycle time"
            return BottleneckDetection(
                constraint_operation_id=max_op,
                utilization_rate=round(max_util, 4),
                suggested_capacity_adjustment=suggestion,
            )
        return None

    def computeDeliveryImpact(
        self, bottleneck: BottleneckDetection
    ) -> DeliveryImpactAssessment:
        delay_days = (bottleneck.utilization_rate - self.UTILIZATION_BOTTLENECK_THRESHOLD) * 10

        if delay_days > 5:
            mitigation = "Add overtime shifts and parallel stations"
        elif delay_days > 2:
            mitigation = "Reallocate resources from non-critical operations"
        else:
            mitigation = "Monitor and adjust scheduling"

        return DeliveryImpactAssessment(
            bottleneck=bottleneck,
            delivery_delay_days=round(delay_days, 1),
            mitigation_recommendation=mitigation,
        )

    def drillDownToEquipment(self, equipment_id: str) -> dict:
        oee = self.getEquipmentOEE(equipment_id)
        return {
            "equipment_id": equipment_id,
            "oee": oee.to_dict(),
            "process_parameters": {},
        }

    def updateOperationUtilization(self, operation_id: str, utilization: float) -> None:
        self._operation_utilization[operation_id] = utilization