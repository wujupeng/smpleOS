from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class SimulationStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SimulationModel:
    aircraft_sn: str = ""
    model_id: str = field(default_factory=lambda: str(uuid4()))
    structural_params: dict[str, float] = field(default_factory=dict)
    aero_params: dict[str, float] = field(default_factory=dict)
    rom_coefficients: dict[str, list[float]] = field(default_factory=dict)
    calibration_count: int = 0
    last_calibrated_at: str = ""
    deviation_accumulated: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "aircraft_sn": self.aircraft_sn,
            "model_id": self.model_id,
            "structural_params": self.structural_params,
            "aero_params": self.aero_params,
            "rom_coefficients_size": {k: len(v) for k, v in self.rom_coefficients.items()},
            "calibration_count": self.calibration_count,
            "last_calibrated_at": self.last_calibrated_at,
            "deviation_accumulated": round(self.deviation_accumulated, 6),
        }


@dataclass
class FlightState:
    timestamp: str = ""
    altitude_m: float = 0.0
    airspeed_ms: float = 0.0
    heading_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    vertical_speed_ms: float = 0.0
    g_load: float = 1.0
    engine_rpm: float = 0.0
    fuel_kg: float = 0.0
    temperature_c: float = 20.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "altitude_m": round(self.altitude_m, 2),
            "airspeed_ms": round(self.airspeed_ms, 2),
            "heading_deg": round(self.heading_deg, 2),
            "pitch_deg": round(self.pitch_deg, 2),
            "roll_deg": round(self.roll_deg, 2),
            "vertical_speed_ms": round(self.vertical_speed_ms, 2),
            "g_load": round(self.g_load, 3),
            "engine_rpm": round(self.engine_rpm, 1),
            "fuel_kg": round(self.fuel_kg, 2),
            "temperature_c": round(self.temperature_c, 1),
        }


@dataclass
class SimulationResult:
    predicted_state: FlightState = field(default_factory=FlightState)
    actual_state: FlightState | None = None
    deviation: dict[str, float] = field(default_factory=dict)
    deviation_exceeds_threshold: bool = False
    simulation_time_ms: float = 0.0
    step_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicted_state": self.predicted_state.to_dict(),
            "actual_state": self.actual_state.to_dict() if self.actual_state else None,
            "deviation": {k: round(v, 6) for k, v in self.deviation.items()},
            "deviation_exceeds_threshold": self.deviation_exceeds_threshold,
            "simulation_time_ms": round(self.simulation_time_ms, 3),
            "step_number": self.step_number,
        }


@dataclass
class CalibrationResult:
    aircraft_sn: str = ""
    previous_deviation: float = 0.0
    new_deviation: float = 0.0
    improvement_pct: float = 0.0
    calibrated_params: list[str] = field(default_factory=list)
    calibrated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "aircraft_sn": self.aircraft_sn,
            "previous_deviation": round(self.previous_deviation, 6),
            "new_deviation": round(self.new_deviation, 6),
            "improvement_pct": round(self.improvement_pct, 2),
            "calibrated_params": self.calibrated_params,
            "calibrated_at": self.calibrated_at,
        }