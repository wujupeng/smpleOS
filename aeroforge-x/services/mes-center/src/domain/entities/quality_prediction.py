from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class PredictionType(str, Enum):
    OPERATION_QUALITY = "operation_quality"
    PART_QUALITY = "part_quality"
    BATCH_QUALITY = "batch_quality"


class PredictionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    VERIFIED = "verified"


class DriftStatus(str, Enum):
    STABLE = "stable"
    WARNING = "warning"
    DRIFTED = "drifted"


@dataclass
class InputFeature:
    name: str
    value: float
    feature_type: str = "process_parameter"
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "feature_type": self.feature_type,
            "unit": self.unit,
        }


@dataclass
class DefectProbability:
    defect_type: str
    probability: float
    severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "defect_type": self.defect_type,
            "probability": round(self.probability, 4),
            "severity": self.severity,
        }


@dataclass
class PredictedResult:
    pass_probability: float = 0.0
    defect_probabilities: list[DefectProbability] = field(default_factory=list)
    risk_level: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_probability": round(self.pass_probability, 4),
            "defect_probabilities": [d.to_dict() for d in self.defect_probabilities],
            "risk_level": self.risk_level,
        }


@dataclass
class SHAPValue:
    feature_name: str
    shap_value: float
    contribution_direction: str = "positive"
    importance_rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "shap_value": round(self.shap_value, 4),
            "contribution_direction": self.contribution_direction,
            "importance_rank": self.importance_rank,
        }


@dataclass
class ActualResult:
    actual_quality: str = ""
    actual_defects: list[str] = field(default_factory=list)
    verified_at: datetime | None = None
    verified_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "actual_quality": self.actual_quality,
            "actual_defects": self.actual_defects,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verified_by": self.verified_by,
        }


@dataclass
class QualityDriftRecord:
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    drift_type: str = "concept_drift"
    metric_name: str = ""
    previous_value: float = 0.0
    current_value: float = 0.0
    drift_magnitude: float = 0.0
    action_taken: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected_at": self.detected_at.isoformat(),
            "drift_type": self.drift_type,
            "metric_name": self.metric_name,
            "previous_value": round(self.previous_value, 4),
            "current_value": round(self.current_value, 4),
            "drift_magnitude": round(self.drift_magnitude, 4),
            "action_taken": self.action_taken,
        }


@dataclass
class ProcessParameterRecommendation:
    parameter_name: str
    current_value: float
    recommended_value: float
    expected_improvement: float
    constraint_satisfied: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "current_value": self.current_value,
            "recommended_value": self.recommended_value,
            "expected_improvement": round(self.expected_improvement, 4),
            "constraint_satisfied": self.constraint_satisfied,
        }


class QualityPrediction(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        work_order_id: str,
        prediction_type: PredictionType,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.work_order_id = work_order_id
        self.prediction_type = prediction_type
        self.input_features: list[InputFeature] = []
        self.predicted_result: PredictedResult | None = None
        self.confidence: float = 0.0
        self.actual_result: ActualResult | None = None
        self.model_version: str = "1.0.0"
        self.shap_values: list[SHAPValue] = []
        self.drift_records: list[QualityDriftRecord] = []
        self.drift_status = DriftStatus.STABLE
        self.parameter_recommendations: list[ProcessParameterRecommendation] = []
        self.status = PredictionStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.predicted_at: datetime | None = None

    def set_input_features(self, features: list[InputFeature]) -> None:
        self.input_features = features

    def set_prediction(
        self,
        result: PredictedResult,
        confidence: float,
        model_version: str = "1.0.0",
    ) -> None:
        self.predicted_result = result
        self.confidence = confidence
        self.model_version = model_version
        self.status = PredictionStatus.COMPLETED
        self.predicted_at = datetime.now(timezone.utc)

    def set_shap_values(self, shap_values: list[SHAPValue]) -> None:
        sorted_values = sorted(shap_values, key=lambda s: abs(s.shap_value), reverse=True)
        for i, sv in enumerate(sorted_values):
            sv.importance_rank = i + 1
            sv.contribution_direction = "positive" if sv.shap_value > 0 else "negative"
        self.shap_values = sorted_values

    def set_actual_result(self, actual: ActualResult) -> None:
        self.actual_result = actual
        self.status = PredictionStatus.VERIFIED

    def add_drift_record(self, record: QualityDriftRecord) -> None:
        self.drift_records.append(record)
        if record.drift_magnitude > 0.15:
            self.drift_status = DriftStatus.DRIFTED
        elif record.drift_magnitude > 0.08:
            self.drift_status = DriftStatus.WARNING

    def set_parameter_recommendations(
        self, recommendations: list[ProcessParameterRecommendation]
    ) -> None:
        self.parameter_recommendations = recommendations

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "work_order_id": self.work_order_id,
            "prediction_type": self.prediction_type.value,
            "status": self.status.value,
            "confidence": round(self.confidence, 4),
            "model_version": self.model_version,
            "drift_status": self.drift_status.value,
            "created_at": self.created_at.isoformat(),
            "predicted_at": self.predicted_at.isoformat() if self.predicted_at else None,
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "input_features": [f.to_dict() for f in self.input_features],
            "predicted_result": self.predicted_result.to_dict() if self.predicted_result else None,
            "actual_result": self.actual_result.to_dict() if self.actual_result else None,
            "shap_values": [s.to_dict() for s in self.shap_values],
            "drift_records": [d.to_dict() for d in self.drift_records],
            "parameter_recommendations": [r.to_dict() for r in self.parameter_recommendations],
        })
        return base