from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


class CalibrationResult(str):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"


class CalibrationStatus(str):
    CURRENT = "current"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    INVALID = "invalid"


@dataclass
class ToolCalibration:
    calibration_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_id: str = ""
    tool_name: str = ""
    calibration_date: date = field(default_factory=date.today)
    next_due_date: date = field(default_factory=date.today)
    result: str = CalibrationResult.PASS
    uncertainty: Decimal | None = None
    certificate_ref: str | None = None
    calibrated_by: str | None = None
    status: str = CalibrationStatus.CURRENT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def check_expiry(self, warning_days: int = 7) -> None:
        today = date.today()
        days_until_due = (self.next_due_date - today).days
        if days_until_due < 0:
            self.status = CalibrationStatus.EXPIRED
            self.domain_events.append({
                "event_type": "tool_calibration.expired",
                "tool_id": self.tool_id,
                "tool_name": self.tool_name,
            })
        elif days_until_due <= warning_days:
            self.status = CalibrationStatus.EXPIRING_SOON
            self.domain_events.append({
                "event_type": "tool_calibration.expiring_soon",
                "tool_id": self.tool_id,
                "days_remaining": days_until_due,
            })
        else:
            self.status = CalibrationStatus.CURRENT
        self.updated_at = datetime.utcnow()

    def invalidate(self, reason: str = "") -> list[str]:
        self.status = CalibrationStatus.INVALID
        self.updated_at = datetime.utcnow()
        self.domain_events.append({
            "event_type": "tool_calibration.invalidated",
            "calibration_id": self.calibration_id,
            "tool_id": self.tool_id,
            "reason": reason,
        })
        return self._trace_affected_work_orders()

    def is_usable(self) -> bool:
        return self.status in (CalibrationStatus.CURRENT, CalibrationStatus.EXPIRING_SOON)

    def _trace_affected_work_orders(self) -> list[str]:
        return []

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events