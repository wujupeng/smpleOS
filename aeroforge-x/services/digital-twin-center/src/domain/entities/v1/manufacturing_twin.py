from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class ManufacturingTwinStatus(str, Enum):
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


@dataclass
class DimensionDeviation:
    parameter_name: str
    design_value: float
    actual_value: float
    tolerance: float
    unit: str

    @property
    def deviation(self) -> float:
        return abs(self.actual_value - self.design_value)

    @property
    def out_of_tolerance(self) -> bool:
        return self.deviation > self.tolerance

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "design_value": self.design_value,
            "actual_value": self.actual_value,
            "tolerance": self.tolerance,
            "deviation": self.deviation,
            "out_of_tolerance": self.out_of_tolerance,
            "unit": self.unit,
        }


@dataclass
class ProcessRecord:
    process_step: str
    operator: str
    timestamp: str
    parameters: dict[str, Any] = field(default_factory=dict)
    result: str = "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "process_step": self.process_step,
            "operator": self.operator,
            "timestamp": self.timestamp,
            "parameters": self.parameters,
            "result": self.result,
        }


class ManufacturingTwin:
    def __init__(
        self,
        aircraft_serial_number: str,
        twin_id: str | None = None,
    ) -> None:
        self.twin_id: str = twin_id or str(uuid4())
        self.aircraft_serial_number: str = aircraft_serial_number
        self.actual_dimensions: dict[str, float] = {}
        self.deviations: list[DimensionDeviation] = []
        self.process_records: list[ProcessRecord] = []
        self.status: ManufacturingTwinStatus = ManufacturingTwinStatus.IN_PRODUCTION
        self.last_sync_time: datetime | None = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def record_actual_dimension(self, parameter_name: str, actual_value: float, design_value: float, tolerance: float, unit: str) -> DimensionDeviation:
        self.actual_dimensions[parameter_name] = actual_value
        deviation = DimensionDeviation(
            parameter_name=parameter_name,
            design_value=design_value,
            actual_value=actual_value,
            tolerance=tolerance,
            unit=unit,
        )
        self.deviations.append(deviation)
        self.updated_at = datetime.now(timezone.utc)
        return deviation

    def add_process_record(self, record: ProcessRecord) -> None:
        self.process_records.append(record)
        self.updated_at = datetime.now(timezone.utc)

    def get_out_of_tolerance_deviations(self) -> list[DimensionDeviation]:
        return [d for d in self.deviations if d.out_of_tolerance]

    def sync_from_manufacturing(self, dimensions: dict[str, float], deviations: list[DimensionDeviation], process_records: list[ProcessRecord]) -> None:
        self.actual_dimensions.update(dimensions)
        self.deviations.extend(deviations)
        self.process_records.extend(process_records)
        self.last_sync_time = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        self.status = ManufacturingTwinStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "twin_id": self.twin_id,
            "aircraft_serial_number": self.aircraft_serial_number,
            "actual_dimensions": self.actual_dimensions,
            "deviations": [d.to_dict() for d in self.deviations],
            "process_records": [r.to_dict() for r in self.process_records],
            "status": self.status.value,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }