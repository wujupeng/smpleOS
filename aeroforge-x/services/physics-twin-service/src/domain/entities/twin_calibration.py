from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import CalibrationStatus


class TwinCalibration(BaseModel):
    calibration_id: str = ""
    runtime_id: str
    model_id: str
    parameter_adjustments: dict[str, Any] = Field(default_factory=dict)
    validation_results: dict[str, Any] = Field(default_factory=dict)
    status: CalibrationStatus = CalibrationStatus.Pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    def execute(self) -> None:
        if self.status != CalibrationStatus.Pending:
            raise ValueError(f"Cannot execute calibration in {self.status.value} state")
        self.status = CalibrationStatus.InProgress

    def complete(self) -> None:
        self.status = CalibrationStatus.Completed
        self.completed_at = datetime.utcnow()

    def fail(self) -> None:
        self.status = CalibrationStatus.Failed
        self.completed_at = datetime.utcnow()

    def validate_calibration(self, holdout_error: float, threshold: float = 0.05) -> bool:
        if holdout_error <= threshold:
            self.validation_results = {"holdout_error": holdout_error, "passed": True}
            return True
        else:
            self.validation_results = {"holdout_error": holdout_error, "passed": False}
            return False