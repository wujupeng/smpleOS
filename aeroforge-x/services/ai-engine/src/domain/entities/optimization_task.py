from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class OptimizationType(str, Enum):
    MULTI_OBJECTIVE = "multi_objective"
    TOPOLOGY = "topology"


class OptimizationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OptimizationAlgorithm(str, Enum):
    NSGA2 = "nsga2"
    MOEAD = "moead"
    PSO = "pso"


@dataclass
class ObjectiveFunction:
    name: str
    direction: str = "minimize"
    weight: float = 1.0
    target_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "direction": self.direction,
            "weight": self.weight,
            "target_value": self.target_value,
        }


@dataclass
class OptimizationConstraint:
    name: str
    constraint_type: str = "inequality"
    operator: str = ">="
    value: float = 0.0
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "constraint_type": self.constraint_type,
            "operator": self.operator,
            "value": self.value,
            "description": self.description,
        }

    def is_satisfied(self, actual: float) -> bool:
        if self.operator == ">=":
            return actual >= self.value
        elif self.operator == "<=":
            return actual <= self.value
        elif self.operator == "==":
            return abs(actual - self.value) < 1e-9
        return True


@dataclass
class DesignVariable:
    name: str
    lower_bound: float = 0.0
    upper_bound: float = 100.0
    initial_value: float | None = None
    step_size: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "initial_value": self.initial_value,
            "step_size": self.step_size,
        }


@dataclass
class ParetoSolution:
    solution_id: str
    variable_values: dict[str, float]
    objective_values: dict[str, float]
    constraint_values: dict[str, float]
    is_feasible: bool = True
    rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "solution_id": self.solution_id,
            "variable_values": self.variable_values,
            "objective_values": self.objective_values,
            "constraint_values": self.constraint_values,
            "is_feasible": self.is_feasible,
            "rank": self.rank,
        }


@dataclass
class OptimizationTask:
    id: str = field(default_factory=lambda: str(uuid4()))
    project_id: str = ""
    tenant_id: str = ""
    optimization_type: OptimizationType = OptimizationType.MULTI_OBJECTIVE
    status: OptimizationStatus = OptimizationStatus.QUEUED
    objectives: list[ObjectiveFunction] = field(default_factory=list)
    constraints: list[OptimizationConstraint] = field(default_factory=list)
    design_variables: list[DesignVariable] = field(default_factory=list)
    algorithm: OptimizationAlgorithm = OptimizationAlgorithm.NSGA2
    max_iterations: int = 100
    population_size: int = 50
    pareto_front: list[ParetoSolution] = field(default_factory=list)
    optimal_solution: ParetoSolution | None = None
    topology_result: dict[str, Any] = field(default_factory=dict)
    iteration_count: int = 0
    convergence_history: list[dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "optimization_type": self.optimization_type.value,
            "status": self.status.value,
            "objectives": [o.to_dict() for o in self.objectives],
            "constraints": [c.to_dict() for c in self.constraints],
            "design_variables": [v.to_dict() for v in self.design_variables],
            "algorithm": self.algorithm.value,
            "max_iterations": self.max_iterations,
            "population_size": self.population_size,
            "pareto_front": [s.to_dict() for s in self.pareto_front],
            "optimal_solution": self.optimal_solution.to_dict() if self.optimal_solution else None,
            "topology_result": self.topology_result,
            "iteration_count": self.iteration_count,
            "convergence_history": self.convergence_history,
            "error_message": self.error_message,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    def start(self) -> None:
        if self.status != OptimizationStatus.QUEUED:
            raise ValueError(f"Cannot start task in {self.status.value} status")
        self.status = OptimizationStatus.RUNNING

    def complete(self, pareto_front: list[ParetoSolution], optimal: ParetoSolution | None = None) -> None:
        self.status = OptimizationStatus.COMPLETED
        self.pareto_front = pareto_front
        self.optimal_solution = optimal
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="optimization.completed",
            aggregate_id=self.id,
            payload={"task_id": self.id, "pareto_size": len(pareto_front)},
        ))

    def fail(self, error: str) -> None:
        self.status = OptimizationStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)