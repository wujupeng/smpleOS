from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PIDParams:
    kp: float = 0.0
    ki: float = 0.0
    kd: float = 0.0
    setpoint: float = 0.0
    output_limits: tuple[float, float] = (-100.0, 100.0)


@dataclass
class LQRParams:
    state_dimension: int = 0
    input_dimension: int = 0
    gain_matrix: list[list[float]] = field(default_factory=list)
    q_weights: list[float] = field(default_factory=list)
    r_weights: list[float] = field(default_factory=list)


@dataclass
class MPCParams:
    prediction_horizon: int = 10
    control_horizon: int = 5
    state_dimension: int = 0
    input_dimension: int = 0
    q_matrix: list[list[float]] = field(default_factory=list)
    r_matrix: list[list[float]] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class StabilityMargins:
    gain_margin_db: float = 0.0
    phase_margin_deg: float = 0.0
    delay_margin_s: float = 0.0
    crossover_frequency_hz: float = 0.0
    is_sufficient: bool = False


@dataclass
class ControlSynthesisResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    aircraft_config: dict[str, Any] = field(default_factory=dict)
    control_type: str = "pid"
    pid_params: PIDParams = field(default_factory=PIDParams)
    lqr_params: LQRParams = field(default_factory=LQRParams)
    mpc_params: MPCParams = field(default_factory=MPCParams)
    stability_margins: StabilityMargins = field(default_factory=StabilityMargins)
    iteration_count: int = 0
    is_margins_satisfied: bool = False
    status: str = "pending"
    created_by: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def complete(self) -> None:
        self.status = "completed"
        self.is_margins_satisfied = self.stability_margins.is_sufficient
        self.updated_at = datetime.utcnow()
        self.domain_events.append({
            "event_type": "control.synthesis.completed",
            "result_id": self.result_id,
            "control_type": self.control_type,
            "is_margins_satisfied": self.is_margins_satisfied,
        })

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.updated_at = datetime.utcnow()

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events