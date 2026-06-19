"""AeroForge-X v5.0 Design Space Explorer Pydantic V2 Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class VisualizeParetoRequest(BaseModel):
    run_id: str
    dimensions: list[str] = Field(default_factory=lambda: ["L_D", "total_weight_kg"])


class FilterParetoRequest(BaseModel):
    run_id: str
    filters: dict[str, dict] = Field(default_factory=dict)


class CorrelationMatrixResponse(BaseModel):
    run_id: str
    variables: list[str]
    matrix: list[list[float]]


class ExportDesignsRequest(BaseModel):
    solution_ids: list[str]
    run_id: str


class ExplorationStepResponse(BaseModel):
    step_id: str
    requirement_id: str
    action_type: str
    action_params: dict
    result_snapshot: dict