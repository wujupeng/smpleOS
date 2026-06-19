"""AeroForge-X v5.0 MDO Optimizer Pydantic V2 Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ObjectiveFunctionInput(BaseModel):
    name: str
    direction: str = Field(pattern="^(Minimize|Maximize)$")
    weight: float = Field(default=1.0, gt=0)
    discipline: str = ""


class DesignVariableInput(BaseModel):
    name: str
    lower: float
    upper: float


class RunMDORequest(BaseModel):
    requirement_id: str = ""
    objectives: list[ObjectiveFunctionInput] = Field(default_factory=list)
    constraints_config: list[dict] = Field(default_factory=list)
    design_variables: list[DesignVariableInput] = Field(default_factory=list)
    population_size: int = Field(default=100, gt=0)
    max_generations: int = Field(default=200, gt=0)


class ParetoFrontResponse(BaseModel):
    run_id: str
    pareto_size: int
    solutions: list[dict]


class SensitivityResultResponse(BaseModel):
    run_id: str
    first_order: dict[str, float]
    total_order: dict[str, float]


class ConvergenceStatusResponse(BaseModel):
    run_id: str
    status: str
    hypervolume_history: list[float]
    pareto_size: int
    generations_completed: int
    best_objectives: dict[str, float]