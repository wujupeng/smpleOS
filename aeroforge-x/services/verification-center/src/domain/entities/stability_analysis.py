from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StabilityResult:
    static_margin_pct_mac: float = 0.0
    neutral_point_pct_mac: float = 0.0
    pitch_stiffness_derivative: float = 0.0
    is_longitudinally_stable: bool = False

    roll_stiffness_derivative: float = 0.0
    dutch_roll_damping_ratio: float = 0.0
    dutch_roll_frequency_hz: float = 0.0
    is_laterally_stable: bool = False

    yaw_stiffness_derivative: float = 0.0
    weathercock_stability: float = 0.0
    is_directionally_stable: bool = False


@dataclass
class ParameterSuggestion:
    parameter: str = ""
    current_value: float = 0.0
    suggested_value: float = 0.0
    reason: str = ""


@dataclass
class StabilityAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    aircraft_config: dict[str, Any] = field(default_factory=dict)
    longitudinal_result: StabilityResult = field(default_factory=StabilityResult)
    lateral_result: StabilityResult = field(default_factory=StabilityResult)
    directional_result: StabilityResult = field(default_factory=StabilityResult)
    suggestions: list[ParameterSuggestion] = field(default_factory=list)
    is_statically_unstable: bool = False
    status: str = "pending"
    created_by: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def complete(self) -> None:
        self.status = "completed"
        self.updated_at = datetime.utcnow()
        self.is_statically_unstable = (
            not self.longitudinal_result.is_longitudinally_stable
            or not self.lateral_result.is_laterally_stable
            or not self.directional_result.is_directionally_stable
        )
        self.domain_events.append({
            "event_type": "stability.analysis.completed",
            "analysis_id": self.analysis_id,
            "is_statically_unstable": self.is_statically_unstable,
        })

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.updated_at = datetime.utcnow()

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events