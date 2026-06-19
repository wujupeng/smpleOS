from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class HarnessType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    AVIONICS_BUS = "avionics_bus"
    POWER_DISTRIBUTION = "power_distribution"
    SENSOR_HARNESS = "sensor_harness"


class HarnessStatus(str, Enum):
    DRAFT = "draft"
    ROUTED = "routed"
    VALIDATED = "validated"
    APPROVED = "approved"
    RELEASED = "released"


@dataclass
class WireSpec:
    wire_id: str = ""
    gauge_awg: int = 20
    conductor_material: str = "copper"
    insulation_type: str = "ptfe"
    length_m: float = 0.0
    voltage_rating_v: float = 600.0
    current_capacity_a: float = 0.0
    color_code: str = ""


@dataclass
class ConnectorSpec:
    connector_id: str = ""
    connector_type: str = "d_sub"
    pin_count: int = 0
    manufacturer: str = ""
    part_number: str = ""


@dataclass
class WireHarnessModel:
    harness_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_ref: str | None = None
    harness_type: HarnessType = HarnessType.PRIMARY
    wire_list: list[WireSpec] = field(default_factory=list)
    connector_list: list[ConnectorSpec] = field(default_factory=list)
    routing_paths: list[dict[str, Any]] = field(default_factory=list)
    status: HarnessStatus = HarnessStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_wire(self, wire: WireSpec) -> None:
        self.wire_list.append(wire)
        self.updated_at = datetime.utcnow()

    def add_connector(self, connector: ConnectorSpec) -> None:
        self.connector_list.append(connector)
        self.updated_at = datetime.utcnow()

    def mark_routed(self) -> None:
        self.status = HarnessStatus.ROUTED
        self.updated_at = datetime.utcnow()

    def calculate_total_weight(self) -> float:
        copper_density = 8.96
        wire_weight = 0.0
        for wire in self.wire_list:
            radius_m = 0.000127 * (92.0 / (39.0 + wire.gauge_awg)) ** 0.5 if wire.gauge_awg > 0 else 0.001
            area_m2 = 3.14159 * radius_m ** 2
            wire_weight += area_m2 * wire.length_m * copper_density
        return wire_weight

    def validate_routing(self) -> list[str]:
        issues = []
        for i, path in enumerate(self.routing_paths):
            if "start_point" not in path or "end_point" not in path:
                issues.append(f"Routing path {i} missing start/end points")
            if path.get("length_m", 0) <= 0:
                issues.append(f"Routing path {i} has invalid length")
        connected_wires = set()
        for path in self.routing_paths:
            if "wire_id" in path:
                connected_wires.add(path["wire_id"])
        for wire in self.wire_list:
            if wire.wire_id and wire.wire_id not in connected_wires:
                issues.append(f"Wire {wire.wire_id} has no routing path")
        return issues