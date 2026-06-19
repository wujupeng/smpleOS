from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class NDTMethod(str):
    ULTRASONIC = "ultrasonic"
    X_RAY = "x_ray"
    THERMAL_IMAGING = "thermal_imaging"
    EDDY_CURRENT = "eddy_current"
    PENETRANT = "penetrant"
    MAGNETIC_PARTICLE = "magnetic_particle"


class NDTResult(str):
    PENDING = "pending"
    ACCEPTABLE = "acceptable"
    MARGINAL = "marginal"
    UNACCEPTABLE = "unacceptable"


class NDTStatus(str):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    REJECTED = "rejected"


@dataclass
class NDTInspection:
    inspection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    serial_number: str = ""
    traveler_ref: str | None = None
    inspection_method: str = NDTMethod.ULTRASONIC
    result: str = NDTResult.PENDING
    defect_description: str | None = None
    inspector_id: str | None = None
    inspector_level: int = 1
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    tool_calibration_ref: str | None = None
    tool_calibration_valid: bool = True
    status: str = NDTStatus.PLANNED
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def record_result(self, result: str, defect_description: str | None = None,
                      inspector_id: str | None = None) -> None:
        if not self.tool_calibration_valid:
            raise ValueError("Cannot record result: tool calibration is expired")
        self.result = result
        self.defect_description = defect_description
        if inspector_id:
            self.inspector_id = inspector_id
        self.status = NDTStatus.COMPLETED
        self.updated_at = datetime.utcnow()

        if result == NDTResult.MARGINAL:
            if self.inspector_level < 2:
                raise ValueError("Marginal results require Level II or III inspector review")
        if result == NDTResult.UNACCEPTABLE:
            self.domain_events.append({
                "event_type": "ndt.unacceptable",
                "inspection_id": self.inspection_id,
                "serial_number": self.serial_number,
                "method": self.inspection_method,
            })

    def review(self, reviewer_id: str, reviewer_level: int = 2) -> None:
        if self.result != NDTResult.MARGINAL:
            raise ValueError("Only marginal results require review")
        if reviewer_level < 2:
            raise ValueError("Review requires Level II or III inspector")
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
        self.status = NDTStatus.REVIEWED
        self.updated_at = datetime.utcnow()

    def complete(self) -> None:
        self.domain_events.append({
            "event_type": "ndt.completed",
            "inspection_id": self.inspection_id,
            "result": self.result,
        })

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events