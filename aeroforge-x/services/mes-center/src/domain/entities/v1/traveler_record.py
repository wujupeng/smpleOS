from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


class TravelerStatus(str):
    IN_PROGRESS = "in_progress"
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"
    NON_CONFORMING = "non_conforming"


@dataclass
class TemperatureReading:
    timestamp: datetime = field(default_factory=datetime.utcnow)
    temperature_c: Decimal = Decimal("0")
    target_temp_c: Decimal = Decimal("0")
    deviation_c: Decimal = Decimal("0")
    is_within_tolerance: bool = True
    duration_s: Decimal = Decimal("0")


@dataclass
class TravelerRecord:
    traveler_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    work_order_id: str = ""
    serial_number: str = ""
    process_step: str = ""
    operator_id: str | None = None
    curing_oven: str | None = None
    quality_inspector: str | None = None
    temperature_profile: list[TemperatureReading] = field(default_factory=list)
    confirmed_at: datetime | None = None
    finalized_at: datetime | None = None
    status: str = TravelerStatus.IN_PROGRESS
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def record_temperature(self, temperature_c: Decimal, target_temp_c: Decimal,
                           tolerance_c: Decimal = Decimal("5"), duration_s: Decimal = Decimal("0")) -> TemperatureReading:
        deviation = temperature_c - target_temp_c
        within = abs(deviation) <= tolerance_c
        reading = TemperatureReading(
            temperature_c=temperature_c,
            target_temp_c=target_temp_c,
            deviation_c=deviation,
            is_within_tolerance=within,
            duration_s=duration_s,
        )
        self.temperature_profile.append(reading)
        self.updated_at = datetime.utcnow()
        if not within:
            self.status = TravelerStatus.NON_CONFORMING
            self.domain_events.append({
                "event_type": "traveler.temperature_deviation",
                "traveler_id": self.traveler_id,
                "deviation_c": float(deviation),
            })
        return reading

    def confirm(self, inspector_id: str) -> None:
        if self.status == TravelerStatus.FINALIZED:
            raise ValueError("Cannot confirm a finalized traveler")
        self.quality_inspector = inspector_id
        self.confirmed_at = datetime.utcnow()
        self.status = TravelerStatus.CONFIRMED
        self.updated_at = datetime.utcnow()

    def finalize(self) -> None:
        if not self.serial_number:
            raise ValueError("Serial number is required to finalize")
        if not self.process_step:
            raise ValueError("Process step is required to finalize")
        if not self.quality_inspector:
            raise ValueError("Quality inspector confirmation is required to finalize")
        if self.status == TravelerStatus.NON_CONFORMING:
            raise ValueError("Cannot finalize a non-conforming traveler")
        self.status = TravelerStatus.FINALIZED
        self.finalized_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.domain_events.append({
            "event_type": "traveler.completed",
            "traveler_id": self.traveler_id,
            "serial_number": self.serial_number,
            "work_order_id": self.work_order_id,
        })

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events