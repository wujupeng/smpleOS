from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TrimResult:
    trim_type: str = "cruise"
    alpha_deg: float = 0.0
    elevator_deflection_deg: float = 0.0
    throttle_pct: float = 0.0
    converged: bool = True
    iteration_count: int = 0


@dataclass
class SimulationState:
    time_s: float = 0.0
    phi_deg: float = 0.0
    theta_deg: float = 0.0
    psi_deg: float = 0.0
    p_deg_s: float = 0.0
    q_deg_s: float = 0.0
    r_deg_s: float = 0.0
    u_m_s: float = 0.0
    v_m_s: float = 0.0
    w_m_s: float = 0.0


@dataclass
class DynamicResponseResult:
    response_type: str = "step"
    settling_time_s: float = 0.0
    rise_time_s: float = 0.0
    overshoot_pct: float = 0.0
    natural_frequency_hz: float = 0.0
    damping_ratio: float = 0.0
    modes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FlightDynamicsAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    aircraft_config: dict[str, Any] = field(default_factory=dict)
    trim_results: list[TrimResult] = field(default_factory=list)
    simulation_results: list[SimulationState] = field(default_factory=list)
    dynamic_response_results: list[DynamicResponseResult] = field(default_factory=list)
    is_uncontrollable: bool = False
    trim_converged: bool = True
    simulation_diverged: bool = False
    status: str = "pending"
    created_by: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def complete(self) -> None:
        self.status = "completed"
        self.updated_at = datetime.utcnow()
        self.domain_events.append({
            "event_type": "flight.dynamics.completed",
            "analysis_id": self.analysis_id,
            "is_uncontrollable": self.is_uncontrollable,
        })

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.updated_at = datetime.utcnow()

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events