"""AeroForge-X v5.0 CFD Surrogate Model Pydantic V2 Schemas"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SurrogateModelHyperparams(BaseModel):
    learning_rate: float = Field(default=1e-3, gt=0)
    epochs: int = Field(default=100, gt=0)
    batch_size: int = Field(default=32, gt=0)
    hidden_layers: list[int] = Field(default_factory=lambda: [128, 128, 64, 64])
    lambda_physics: float = Field(default=1.0, ge=0)
    lambda_boundary: float = Field(default=1.0, ge=0)


class TrainSurrogateModelRequest(BaseModel):
    architecture: str = Field(default="PINN", pattern="^(PINN|DeepONet|Transformer)$")
    model_id: str | None = None
    dataset_path: str = ""
    input_dimensions: list[str] = Field(default_factory=lambda: ["alpha", "beta", "mach", "reynolds"])
    output_dimensions: list[str] = Field(default_factory=lambda: ["CL", "CD", "CM", "CY", "Cl", "Cn"])
    hyperparams: SurrogateModelHyperparams | None = None


class AeroPredictRequest(BaseModel):
    alpha: float = Field(default=0.0)
    beta: float = Field(default=0.0)
    mach: float = Field(default=0.0)
    reynolds: float = Field(default=1e6, gt=0)
    altitude: float = Field(default=0.0, ge=0)
    dynamic_pressure: float = Field(default=0.0, ge=0)


class AeroCoefficientsPredictionResponse(BaseModel):
    CL: float
    CD: float
    CM: float
    CY: float = 0.0
    Cl: float = 0.0
    Cn: float = 0.0
    confidence: float
    is_fallback: bool
    fallback_reason: str = ""


class ModelQualityMetricsResponse(BaseModel):
    model_id: str
    r_squared: float
    rmse: dict
    prediction_interval_coverage: float
    test_set_size: int
    last_validated_at: str | None = None