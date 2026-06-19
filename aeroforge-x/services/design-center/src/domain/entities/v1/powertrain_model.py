from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PowertrainStatus(str, Enum):
    DRAFT = "draft"
    CONFIGURED = "configured"
    VALIDATED = "validated"
    APPROVED = "approved"
    RELEASED = "released"


@dataclass
class MotorSpec:
    motor_type: str = "brushless_outrunner"
    max_thrust_n: float = 0.0
    kv_rating: float = 0.0
    weight_kg: float = 0.0
    voltage_range: tuple[float, float] = (0.0, 0.0)
    efficiency_pct: float = 0.0


@dataclass
class BatterySpec:
    chemistry: str = "lipo"
    capacity_mah: float = 0.0
    cell_count: int = 0
    voltage_v: float = 0.0
    max_discharge_c: float = 0.0
    weight_kg: float = 0.0


@dataclass
class ESCSpec:
    max_current_a: float = 0.0
    voltage_range: tuple[float, float] = (0.0, 0.0)
    weight_kg: float = 0.0
    protocol: str = "dshot600"


@dataclass
class PowertrainModel:
    powertrain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_ref: str | None = None
    motor_spec: MotorSpec = field(default_factory=MotorSpec)
    battery_spec: BatterySpec = field(default_factory=BatterySpec)
    esc_spec: ESCSpec = field(default_factory=ESCSpec)
    cable_routing: list[dict[str, Any]] = field(default_factory=list)
    thrust_params: dict[str, Any] = field(default_factory=dict)
    fuel_system: dict[str, Any] = field(default_factory=dict)
    propeller_params: dict[str, Any] = field(default_factory=dict)
    status: PowertrainStatus = PowertrainStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def mark_configured(self) -> None:
        self.status = PowertrainStatus.CONFIGURED
        self.updated_at = datetime.utcnow()

    def calculate_endurance(self, cruise_power_w: float) -> float | None:
        if self.battery_spec.capacity_mah <= 0 or self.battery_spec.voltage_v <= 0:
            return None
        energy_wh = (self.battery_spec.capacity_mah / 1000.0) * self.battery_spec.voltage_v
        if cruise_power_w <= 0:
            return None
        return (energy_wh / cruise_power_w) * 60.0

    def calculate_max_thrust(self, motor_count: int = 1) -> float:
        return self.motor_spec.max_thrust_n * motor_count