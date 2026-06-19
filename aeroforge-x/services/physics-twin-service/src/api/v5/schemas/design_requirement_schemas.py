"""AeroForge-X v5.0 Design Requirement Pydantic V2 Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ParseRequirementRequest(BaseModel):
    requirement_text: str = Field(..., min_length=1, description="Natural language design requirement")
    project_id: str = Field(default="", description="Project identifier")


class DesignRequirementResponse(BaseModel):
    requirement_id: str
    version: int
    requirement_text: str
    range_km: float | None = None
    payload_kg: float | None = None
    cruise_speed_kmh: float | None = None
    ceiling_m: float | None = None
    cost_target: float | None = None
    feasibility_status: str = "Pending"
    project_id: str = ""


class FeasibilityCheckResponse(BaseModel):
    requirement_id: str
    is_feasible: bool
    violated_constraints: list[str]
    suggested_adjustments: dict[str, float]


class ConflictReportResponse(BaseModel):
    requirement_id: str
    conflicts: list[dict]
    resolution_suggestions: list[str]