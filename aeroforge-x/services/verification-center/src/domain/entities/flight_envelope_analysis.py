from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LimitSpeeds:
    vs1_ms: float = 0.0
    vs0_ms: float = 0.0
    va_ms: float = 0.0
    vc_ms: float = 0.0
    vd_ms: float = 0.0
    vne_ms: float = 0.0


@dataclass
class LimitLoadFactors:
    n_max_positive: float = 3.5
    n_max_negative: float = -1.5
    n_ultimate_positive: float = 5.25
    n_ultimate_negative: float = -2.25


@dataclass
class VnDiagramPoint:
    speed_ms: float = 0.0
    load_factor: float = 0.0
    label: str = ""


@dataclass
class EnvelopeViolation:
    violation_type: str = ""
    speed_ms: float = 0.0
    load_factor: float = 0.0
    description: str = ""
    severity: str = "warning"


@dataclass
class FlightEnvelopeAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    aircraft_config: dict[str, Any] = field(default_factory=dict)
    limit_speeds: LimitSpeeds = field(default_factory=LimitSpeeds)
    limit_load_factors: LimitLoadFactors = field(default_factory=LimitLoadFactors)
    vn_diagram: list[VnDiagramPoint] = field(default_factory=list)
    gust_envelope: list[VnDiagramPoint] = field(default_factory=list)
    violations: list[EnvelopeViolation] = field(default_factory=list)
    is_airworthy: bool = True
    status: str = "pending"
    created_by: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def complete(self) -> None:
        self.status = "completed"
        self.is_airworthy = len([v for v in self.violations if v.severity == "critical"]) == 0
        self.updated_at = datetime.utcnow()
        self.domain_events.append({
            "event_type": "envelope.generated",
            "analysis_id": self.analysis_id,
            "is_airworthy": self.is_airworthy,
        })

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.updated_at = datetime.utcnow()

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events