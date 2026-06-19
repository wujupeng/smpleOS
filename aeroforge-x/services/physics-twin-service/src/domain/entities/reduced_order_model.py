from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import ReductionMethod, ValidationStatus


class ReducedOrderModel(BaseModel):
    rom_id: str = ""
    source_model_id: str
    method: ReductionMethod
    accuracy: float = 0.0
    validation_error: float = 1.0
    validation_status: ValidationStatus = ValidationStatus.Pending
    deployment_status: str = "NotDeployed"
    deployed_ref: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def validate_rom(self, error_threshold: float = 0.05) -> None:
        if self.validation_error <= error_threshold:
            self.validation_status = ValidationStatus.Passed
        else:
            self.validation_status = ValidationStatus.Failed

    def deploy(self, runtime_id: str) -> None:
        if self.validation_status != ValidationStatus.Passed:
            raise ValueError("Cannot deploy ROM that has not passed validation")
        self.deployment_status = "Deployed"
        self.deployed_ref = runtime_id

    def hot_swap(self, runtime_id: str) -> None:
        if self.validation_status != ValidationStatus.Passed:
            raise ValueError("Cannot hot-swap ROM that has not passed validation")
        self.deployment_status = "Deployed"
        self.deployed_ref = runtime_id