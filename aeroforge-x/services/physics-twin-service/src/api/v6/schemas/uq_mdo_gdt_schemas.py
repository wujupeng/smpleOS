"""AeroForge-X V6.0 UQ/MDO/GD&T Pydantic V2 Schemas
REQ-ENG-010, REQ-E-ENH-001~020
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class RegisterUQMethodRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    method_id: str = Field(min_length=1)
    method_type: str = Field(pattern="^(BayesianPINN|MCDropout|Ensemble)$")
    surrogate_model_id: str = ""
    hyperparameters: dict = Field(default_factory=dict)
    confidence_level: float = Field(default=0.95, gt=0, le=1.0)
    cov_threshold: float = Field(default=0.10, gt=0)


class UQPredictRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    inputs: dict
    method: str = ""


class UQPredictionResponse(BaseModel):
    aero_coefficients: dict = Field(default_factory=dict)
    prediction_intervals: dict = Field(default_factory=dict)
    coefficient_of_variation: float = 0.0
    uq_method: str = ""
    is_high_uncertainty: bool = False


class HotSwapUQRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    method_id: str = Field(min_length=1)


class HotSwapUQResponse(BaseModel):
    old_method_id: str
    new_method_id: str
    swapped: bool


class MDO7DRunRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    requirement_id: str = Field(min_length=1)
    design_variables: dict = Field(default_factory=dict)
    active_discipline_count: int = Field(default=7, ge=4, le=7)
    population_size: int = Field(default=100, gt=0)
    max_generations: int = Field(default=300, gt=0)


class MDO7DRunResponse(BaseModel):
    design_parameters: dict = Field(default_factory=dict)
    objective_values: dict = Field(default_factory=dict)
    uncertainty_on_objectives: dict = Field(default_factory=dict)
    is_pareto_optimal: bool = False


class DisciplineSensitivityResponse(BaseModel):
    run_id: str
    first_order_indices: dict = Field(default_factory=dict)
    total_order_indices: dict = Field(default_factory=dict)
    per_discipline_breakdown: dict = Field(default_factory=dict)


class GDTAnnotationCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    part_id: str = Field(min_length=1)
    tolerance_type: str = Field(pattern="^(Form|Orientation|Location)$")
    tolerance_name: str = Field(min_length=1)
    tolerance_value: float = Field(gt=0)
    unit: str = "mm"


class GDTAnnotationResponse(BaseModel):
    annotation_id: str
    part_id: str
    tolerance_type: str
    tolerance_name: str
    tolerance_value: float
    unit: str = "mm"
    datum_references: list[str] = Field(default_factory=list)
    linked_operation_id: str = ""


class DatumDefinitionRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    part_id: str = Field(min_length=1)
    datum_type: str = Field(pattern="^(Primary|Secondary|Tertiary)$")
    datum_feature: str = Field(min_length=1)
    datum_reference_frame: str = ""


class ToleranceChainAnalysisRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    assembly_id: str = Field(min_length=1)
    steps: list[dict]
    analysis_method: str = Field(pattern="^(WorstCase|Statistical_RSS)$", default="Statistical_RSS")
    target_assembly_tolerance: float = Field(ge=0)


class ToleranceChainAnalysisResponse(BaseModel):
    chain_id: str
    worst_case_result: float = 0.0
    statistical_result: float = 0.0
    is_within_tolerance: bool = False
    contributing_tolerances: list[dict] = Field(default_factory=list)


class MeasurementDeviationRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    annotation_id: str = Field(min_length=1)
    actual_value: float