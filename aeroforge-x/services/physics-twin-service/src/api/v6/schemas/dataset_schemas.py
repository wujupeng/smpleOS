"""AeroForge-X V6.1 Dataset Governance Pydantic V2 Schemas
REQ-ENG-010, REQ-DG-001~013
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class DatasetVersionCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    dataset_id: str = Field(min_length=1)
    major: int = Field(default=1, ge=1)
    minor: int = Field(default=0, ge=0)
    patch: int = Field(default=0, ge=0)
    source: str = ""
    sample_count: int = Field(default=0, ge=0)
    feature_schema: dict = Field(default_factory=dict)
    change_summary: str = ""


class DatasetVersionResponse(BaseModel):
    dataset_version_id: str
    dataset_id: str
    major: int
    minor: int
    patch: int
    source: str
    sample_count: int
    feature_schema: dict = Field(default_factory=dict)
    change_summary: str = ""
    fingerprint: dict | None = None
    created_at: str = ""


class DatasetFingerprintRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    dataset_version_id: str = Field(min_length=1)
    feature_data: dict[str, list[float]]


class DatasetFingerprintResponse(BaseModel):
    dataset_version_id: str
    feature_statistics: dict = Field(default_factory=dict)


class DatasetVersionCompareRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    source_version_id: str = Field(min_length=1)
    target_version_id: str = Field(min_length=1)


class DatasetDeltaReportResponse(BaseModel):
    source_version_id: str
    target_version_id: str
    added_samples: int = 0
    removed_samples: int = 0
    modified_samples: int = 0
    schema_changes: list[dict] = Field(default_factory=list)


class ModelDatasetLinkRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    model_id: str = Field(min_length=1)
    dataset_version_id: str = Field(min_length=1)


class ModelDatasetLinkResponse(BaseModel):
    link_id: str
    model_id: str
    dataset_version_id: str
    linked_at: str = ""


class FeatureDriftDetectRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    dataset_id: str = Field(min_length=1)
    reference_dataset_id: str = Field(min_length=1)
    reference_data: dict[str, list[float]]
    current_data: dict[str, list[float]]
    alpha: float | None = None


class ConceptDriftDetectRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    dataset_id: str = Field(min_length=1)
    reference_dataset_id: str = Field(min_length=1)
    baseline_errors: list[float]
    current_errors: list[float]
    threshold_sigma: float | None = None


class PSIDetectRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    dataset_id: str = Field(min_length=1)
    reference_dataset_id: str = Field(min_length=1)
    reference_data: dict[str, list[float]]
    current_data: dict[str, list[float]]
    n_bins: int = Field(default=10, gt=0)


class DriftDetectionResponse(BaseModel):
    dataset_id: str
    reference_dataset_id: str
    drift_type: str
    ks_statistic: float = 0.0
    ks_p_value: float = 1.0
    psi_value: float = 0.0
    concept_drift_magnitude: float = 0.0
    is_drift_detected: bool = False
    affected_features: list[str] = Field(default_factory=list)
    recommended_action: str = ""


class QualityScoreRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    dataset_id: str = Field(min_length=1)
    missing_value_ratio: float = Field(default=0.0, ge=0, le=1)
    constraint_violation_ratio: float = Field(default=0.0, ge=0, le=1)
    data_age_days: float = Field(default=0.0, ge=0)
    max_acceptable_age_days: float = Field(default=365.0, gt=0)
    design_space_coverage: float = Field(default=1.0, ge=0, le=1)


class QualityScoreResponse(BaseModel):
    assessment_id: str
    dataset_id: str
    overall_score: float
    completeness_score: float
    consistency_score: float
    timeliness_score: float
    representativeness_score: float
    improvement_recommendations: str = ""