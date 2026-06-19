"""AeroForge-X V6.1 PHMModelConfidenceService

Enhances PHM predictions with (RUL, Confidence, DataQuality) triple.
Supports low-confidence flagging, UQ/Dataset Quality integration,
and maintenance decision auditability.

REQ-MC-001~009
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConfidenceInterval:
    lower: float
    upper: float
    confidence_level: float = 0.95
    method: str = "EnsembleVariance"

    def to_dict(self) -> dict:
        return {
            "lower": self.lower,
            "upper": self.upper,
            "confidence_level": self.confidence_level,
            "method": self.method,
        }

    def width(self) -> float:
        return self.upper - self.lower


@dataclass
class PHMDataQualityScore:
    prediction_id: str
    sensor_completeness: float = 100.0
    calibration_currency: float = 100.0
    operating_condition_coverage: float = 100.0
    failure_data_representativeness: float = 100.0
    overall_score: float = 100.0

    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id,
            "sensor_completeness": self.sensor_completeness,
            "calibration_currency": self.calibration_currency,
            "operating_condition_coverage": self.operating_condition_coverage,
            "failure_data_representativeness": self.failure_data_representativeness,
            "overall_score": round(self.overall_score, 2),
        }


@dataclass
class RULPredictionWithConfidence:
    prediction_id: str
    component_id: str
    rul_point_estimate: float
    confidence_interval: Optional[ConfidenceInterval] = None
    data_quality_score: Optional[PHMDataQualityScore] = None
    is_low_confidence: bool = False
    confidence_level: float = 0.95

    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id,
            "component_id": self.component_id,
            "rul_point_estimate": self.rul_point_estimate,
            "confidence_interval": self.confidence_interval.to_dict() if self.confidence_interval else None,
            "data_quality_score": self.data_quality_score.to_dict() if self.data_quality_score else None,
            "is_low_confidence": self.is_low_confidence,
            "confidence_level": self.confidence_level,
        }


@dataclass
class MaintenanceDecisionAudit:
    audit_id: str
    prediction_id: str
    rul_point_estimate: float
    confidence_lower: float
    confidence_upper: float
    data_quality_score: float
    decision_threshold: float
    decision_outcome: str = ""
    engineer_approval: str = ""
    review_required: bool = False
    review_decision: str = ""
    reviewer: str = ""
    reviewed_at: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "audit_id": self.audit_id,
            "prediction_id": self.prediction_id,
            "rul_point_estimate": self.rul_point_estimate,
            "confidence_lower": self.confidence_lower,
            "confidence_upper": self.confidence_upper,
            "data_quality_score": self.data_quality_score,
            "decision_threshold": self.decision_threshold,
            "decision_outcome": self.decision_outcome,
            "engineer_approval": self.engineer_approval,
            "review_required": self.review_required,
            "review_decision": self.review_decision,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "created_at": self.created_at,
        }


@dataclass
class LowConfidenceReview:
    prediction_id: str
    confidence_width_pct: float
    review_required: bool = False
    review_decision: str = ""
    reviewer: str = ""
    reviewed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id,
            "confidence_width_pct": self.confidence_width_pct,
            "review_required": self.review_required,
            "review_decision": self.review_decision,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
        }


LOW_CONFIDENCE_DQ_THRESHOLD = 70.0
CI_WIDTH_PCT_THRESHOLD = 0.30
INFLATION_FACTOR = 1.5
DATASET_QUALITY_IMPACT_PCT = 0.03


class PHMModelConfidenceService:

    def __init__(self) -> None:
        self._predictions: dict[str, RULPredictionWithConfidence] = {}
        self._audits: dict[str, MaintenanceDecisionAudit] = {}
        self._reviews: list[LowConfidenceReview] = []
        self._confidence_events: list[dict] = []

    def predictWithConfidence(
        self,
        component_id: str,
        rul_point_estimate: float,
        ensemble_predictions: list[float] | None = None,
        confidence_level: float = 0.95,
    ) -> RULPredictionWithConfidence:
        prediction_id = f"PHM-{uuid.uuid4().hex[:8]}"

        ci = self.computeConfidenceInterval(
            rul_point_estimate, ensemble_predictions or [], confidence_level
        )

        dq = self.computeDataQualityScore(prediction_id)

        is_low = dq.overall_score < LOW_CONFIDENCE_DQ_THRESHOLD

        if is_low:
            inflated_width = ci.width() * INFLATION_FACTOR
            half = inflated_width / 2.0
            ci = ConfidenceInterval(
                lower=rul_point_estimate - half,
                upper=rul_point_estimate + half,
                confidence_level=confidence_level,
                method=ci.method,
            )

        prediction = RULPredictionWithConfidence(
            prediction_id=prediction_id,
            component_id=component_id,
            rul_point_estimate=rul_point_estimate,
            confidence_interval=ci,
            data_quality_score=dq,
            is_low_confidence=is_low,
            confidence_level=confidence_level,
        )
        self._predictions[prediction_id] = prediction
        return prediction

    def computeConfidenceInterval(
        self,
        rul_point_estimate: float,
        ensemble_predictions: list[float],
        confidence_level: float = 0.95,
    ) -> ConfidenceInterval:
        if len(ensemble_predictions) < 2:
            margin = rul_point_estimate * 0.1
            return ConfidenceInterval(
                lower=max(0, rul_point_estimate - margin),
                upper=rul_point_estimate + margin,
                confidence_level=confidence_level,
                method="PointEstimateMargin",
            )

        import numpy as np

        preds = np.array(ensemble_predictions, dtype=float)
        std = float(np.std(preds))

        z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_scores.get(confidence_level, 1.96)

        margin = z * std
        return ConfidenceInterval(
            lower=max(0, rul_point_estimate - margin),
            upper=rul_point_estimate + margin,
            confidence_level=confidence_level,
            method="EnsembleVariance",
        )

    def computeDataQualityScore(
        self,
        prediction_id: str,
        sensor_completeness: float = 100.0,
        calibration_currency: float = 100.0,
        operating_condition_coverage: float = 100.0,
        failure_data_representativeness: float = 100.0,
    ) -> PHMDataQualityScore:
        overall = (
            sensor_completeness * 0.30
            + calibration_currency * 0.25
            + operating_condition_coverage * 0.25
            + failure_data_representativeness * 0.20
        )

        return PHMDataQualityScore(
            prediction_id=prediction_id,
            sensor_completeness=sensor_completeness,
            calibration_currency=calibration_currency,
            operating_condition_coverage=operating_condition_coverage,
            failure_data_representativeness=failure_data_representativeness,
            overall_score=overall,
        )

    def flagLowConfidence(
        self, prediction_id: str
    ) -> Optional[LowConfidenceReview]:
        prediction = self._predictions.get(prediction_id)
        if prediction is None:
            return None

        if not prediction.is_low_confidence:
            return None

        ci = prediction.confidence_interval
        if ci is None or prediction.rul_point_estimate == 0:
            return None

        width_pct = ci.width() / prediction.rul_point_estimate
        review_required = width_pct > CI_WIDTH_PCT_THRESHOLD

        review = LowConfidenceReview(
            prediction_id=prediction_id,
            confidence_width_pct=width_pct,
            review_required=review_required,
        )
        self._reviews.append(review)
        return review

    def integrateDatasetQuality(
        self, prediction_id: str, dataset_quality_score: float
    ) -> Optional[PHMDataQualityScore]:
        prediction = self._predictions.get(prediction_id)
        if prediction is None or prediction.data_quality_score is None:
            return None

        dq = prediction.data_quality_score
        deficit = max(0, 70.0 - dataset_quality_score)
        reduction = deficit / 10.0 * DATASET_QUALITY_IMPACT_PCT * 100.0

        dq.overall_score = max(0, dq.overall_score - reduction)
        if dq.overall_score < LOW_CONFIDENCE_DQ_THRESHOLD:
            prediction.is_low_confidence = True

        return dq

    def logMaintenanceDecision(
        self,
        prediction_id: str,
        decision_threshold: float,
        decision_outcome: str,
        engineer_approval: str = "",
    ) -> MaintenanceDecisionAudit:
        prediction = self._predictions.get(prediction_id)
        if prediction is None:
            raise ValueError(f"Prediction not found: {prediction_id}")

        audit = MaintenanceDecisionAudit(
            audit_id=f"MDA-{uuid.uuid4().hex[:8]}",
            prediction_id=prediction_id,
            rul_point_estimate=prediction.rul_point_estimate,
            confidence_lower=prediction.confidence_interval.lower if prediction.confidence_interval else 0.0,
            confidence_upper=prediction.confidence_interval.upper if prediction.confidence_interval else 0.0,
            data_quality_score=prediction.data_quality_score.overall_score if prediction.data_quality_score else 100.0,
            decision_threshold=decision_threshold,
            decision_outcome=decision_outcome,
            engineer_approval=engineer_approval,
            review_required=prediction.is_low_confidence,
        )
        self._audits[audit.audit_id] = audit
        return audit

    def queryDecisionAuditTrail(self, component_id: str) -> list[MaintenanceDecisionAudit]:
        results = []
        for audit in self._audits.values():
            pred = self._predictions.get(audit.prediction_id)
            if pred and pred.component_id == component_id:
                results.append(audit)
        return results

    def getPrediction(self, prediction_id: str) -> Optional[RULPredictionWithConfidence]:
        return self._predictions.get(prediction_id)