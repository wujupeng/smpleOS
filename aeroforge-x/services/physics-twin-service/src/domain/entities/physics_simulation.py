from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import SimulationStatus, SolverType


class SimulationResult(BaseModel):
    result_id: str = ""
    simulation_id: str
    scalar_results: dict[str, Any] = Field(default_factory=dict)
    field_results_ref: str = ""
    convergence_history: dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class PhysicsSimulation(BaseModel):
    simulation_id: str = ""
    model_id: str
    solver_type: SolverType
    config: dict[str, Any] = Field(default_factory=dict)
    boundary_conditions: dict[str, Any] = Field(default_factory=dict)
    status: SimulationStatus = SimulationStatus.Queued
    results_ref: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    def submit(self) -> None:
        if self.status != SimulationStatus.Queued:
            raise ValueError(f"Cannot submit simulation in {self.status.value} state")
        self.status = SimulationStatus.Running

    def cancel(self) -> None:
        if self.status not in (SimulationStatus.Queued, SimulationStatus.Running):
            raise ValueError(f"Cannot cancel simulation in {self.status.value} state")
        self.status = SimulationStatus.Failed

    def complete(self) -> None:
        self.status = SimulationStatus.Completed
        self.completed_at = datetime.utcnow()

    def fail(self) -> None:
        self.status = SimulationStatus.Failed
        self.completed_at = datetime.utcnow()