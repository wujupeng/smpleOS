"""AeroForge-X v5.0 AeroGPT Designer Pydantic V2 Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SuggestDesignsRequest(BaseModel):
    requirement_id: str
    max_suggestions: int = Field(default=5, gt=0, le=20)


class DesignSuggestionResponse(BaseModel):
    suggestion_id: str
    requirement_id: str
    compliance_score: float
    satisfied_constraints: list[str]
    violated_constraints: list[str]
    reasoning: list[str]
    source_designs: list[str]
    configuration: dict


class IterateDesignRequest(BaseModel):
    modifications: dict = Field(default_factory=dict)


class AircraftConfigurationResponse(BaseModel):
    configuration_id: str
    geometry_id: str | None = None
    requirement_id: str | None = None
    structure_params: dict
    propulsion_params: dict
    control_params: dict
    overall_score: float