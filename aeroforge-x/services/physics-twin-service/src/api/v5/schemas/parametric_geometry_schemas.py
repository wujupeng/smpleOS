"""AeroForge-X v5.0 Parametric Geometry Pydantic V2 Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DesignParametersInput(BaseModel):
    wing_span: float = Field(..., gt=0, le=200)
    wing_area: float = Field(..., gt=0, le=1000)
    wing_aspect_ratio: float = Field(..., gt=0, le=50)
    wing_sweep_angle: float = Field(..., ge=0, le=70)
    wing_taper_ratio: float = Field(..., gt=0, le=1)
    fuselage_length: float = Field(..., gt=0, le=150)
    fuselage_diameter: float = Field(..., gt=0, le=15)
    horizontal_tail_area: float | None = Field(default=None, gt=0)
    vertical_tail_area: float | None = Field(default=None, gt=0)
    engine_count: int = Field(default=2, ge=1, le=8)
    engine_thrust: float = Field(default=25000.0, gt=0)


class GenerateGeometryRequest(BaseModel):
    parameters: DesignParametersInput
    requirement_id: str | None = None


class AircraftGeometryResponse(BaseModel):
    geometry_id: str
    topology_hash: str
    export_formats: list[str]
    minio_ref: str
    parameters: dict


class ExportGeometryRequest(BaseModel):
    format: str = Field(default="STEP", pattern="^(STEP|IGES|OpenVSP)$")


class ManufacturingViolationResponse(BaseModel):
    violation_type: str
    parameter: str
    current_value: float
    required_value: float
    message: str


class ManufacturingCheckResponse(BaseModel):
    geometry_id: str
    passed: bool
    violations: list[ManufacturingViolationResponse]
    nearest_feasible_geometry: str | None = None