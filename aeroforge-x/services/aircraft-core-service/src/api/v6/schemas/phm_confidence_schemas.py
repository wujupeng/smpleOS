"""AeroForge-X V6.1 PHM Model Confidence & Incremental Propagation Pydantic V2 Schemas
REQ-ENG-010, REQ-MC-001~009, REQ-IC-001~010
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class PHMPredictRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    component_id: str = Field(min_length=1)
    rul_point_estimate: float = Field(gt=0)
    ensemble_predictions: list[float] | None = None
    confidence_level: float = Field(default=0.95, gt=0, le=1.0)


class ConfidenceIntervalResponse(BaseModel):
    lower: float
    upper: float
    confidence_level: float = 0.95
    method: str = "EnsembleVariance"


class PHMDataQualityResponse(BaseModel):
    prediction_id: str
    sensor_completeness: float = 100.0
    calibration_currency: float = 100.0
    operating_condition_coverage: float = 100.0
    failure_data_representativeness: float = 100.0
    overall_score: float = 100.0


class PHMPredictionResponse(BaseModel):
    prediction_id: str
    component_id: str
    rul_point_estimate: float
    confidence_interval: ConfidenceIntervalResponse | None = None
    data_quality_score: PHMDataQualityResponse | None = None
    is_low_confidence: bool = False
    confidence_level: float = 0.95


class LowConfidenceReviewResponse(BaseModel):
    prediction_id: str
    confidence_width_pct: float
    review_required: bool = False
    review_decision: str = ""
    reviewer: str = ""


class MaintenanceDecisionLogRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    prediction_id: str = Field(min_length=1)
    decision_threshold: float = Field(gt=0)
    decision_outcome: str = Field(min_length=1)
    engineer_approval: str = ""


class MaintenanceDecisionAuditResponse(BaseModel):
    audit_id: str
    prediction_id: str
    rul_point_estimate: float
    confidence_lower: float
    confidence_upper: float
    data_quality_score: float
    decision_threshold: float
    decision_outcome: str
    engineer_approval: str = ""
    review_required: bool = False


class BOMNodeRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    node_id: str = Field(min_length=1)
    parent_ids: list[str] = Field(default_factory=list)
    propagation_rules: dict = Field(default_factory=dict)
    config_view_type: str = "Design"


class BOMEdgeRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    edge_type: str = Field(pattern="^(Derivation|Propagation)$", default="Derivation")
    rule_id: str = ""


class BuildDependencyGraphRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    nodes: list[BOMNodeRequest]
    edges: list[BOMEdgeRequest]


class IncrementalPropagationRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    changed_node_ids: list[str]
    change_data: dict = Field(default_factory=dict)


class BatchPropagationRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    batch_changes: list[dict]


class PropagationResultResponse(BaseModel):
    change_id: str
    affected_node_count: int = 0
    propagation_duration_ms: float = 0.0
    is_incremental: bool = True
    fallback_triggered: bool = False
    inconsistent_nodes: list[str] = Field(default_factory=list)


class AffectedSubtreeResponse(BaseModel):
    root_node_id: str
    affected_nodes: list[str] = Field(default_factory=list)
    topological_order: list[str] = Field(default_factory=list)