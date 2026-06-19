from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Any

from ..entities.quality_prediction import (
    ActualResult,
    DefectProbability,
    DriftStatus,
    InputFeature,
    PredictedResult,
    PredictionType,
    ProcessParameterRecommendation,
    QualityDriftRecord,
    QualityPrediction,
    SHAPValue,
)

_DEFECT_TYPES = [
    "porosity", "crack", "dimensional_deviation",
    "surface_defect", "inclusion", "warpage",
]

_PROCESS_PARAMS = [
    "forging_temperature", "press_speed", "holding_time",
    "cooling_rate", "die_temperature", "lubrication_amount",
]


class QualityPredictionService:
    def __init__(self) -> None:
        self._predictions: dict[str, QualityPrediction] = {}
        self._model_versions: dict[str, dict[str, Any]] = {}
        self._drift_threshold_warning = 0.08
        self._drift_threshold_critical = 0.15

    def build_quality_model(
        self,
        tenant_id: str,
        project_id: str,
        model_type: str = "xgboost",
    ) -> dict[str, Any]:
        model_id = f"qm-{tenant_id}-{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        version = f"{len(self._model_versions) + 1}.0.0"
        self._model_versions[model_id] = {
            "model_id": model_id,
            "model_type": model_type,
            "version": version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "accuracy": round(random.uniform(0.88, 0.96), 4),
            "precision": round(random.uniform(0.85, 0.94), 4),
            "recall": round(random.uniform(0.83, 0.92), 4),
            "f1_score": round(random.uniform(0.84, 0.93), 4),
            "cross_val_scores": [round(random.uniform(0.85, 0.95), 4) for _ in range(5)],
            "feature_count": len(_PROCESS_PARAMS) + 4,
            "training_samples": random.randint(5000, 50000),
        }
        return self._model_versions[model_id]

    def predict_quality(
        self,
        tenant_id: str,
        project_id: str,
        work_order_id: str,
        prediction_type: PredictionType,
        input_features: list[InputFeature],
        model_version: str = "1.0.0",
    ) -> QualityPrediction:
        prediction = QualityPrediction(
            tenant_id=tenant_id,
            project_id=project_id,
            work_order_id=work_order_id,
            prediction_type=prediction_type,
        )
        prediction.set_input_features(input_features)

        feature_sum = sum(f.value for f in input_features)
        feature_count = max(len(input_features), 1)
        normalized = min(max((feature_sum / feature_count) / 100.0, 0.0), 1.0)

        pass_prob = round(0.6 + normalized * 0.35 + random.uniform(-0.05, 0.05), 4)
        pass_prob = min(max(pass_prob, 0.1), 0.99)

        defect_probs: list[DefectProbability] = []
        remaining = 1.0 - pass_prob
        for i, dt in enumerate(_DEFECT_TYPES):
            if i == len(_DEFECT_TYPES) - 1:
                prob = max(remaining, 0.0)
            else:
                prob = remaining * random.uniform(0.1, 0.4)
                remaining -= prob
            if prob > 0.001:
                severity = "high" if prob > 0.1 else ("medium" if prob > 0.03 else "low")
                defect_probs.append(DefectProbability(
                    defect_type=dt, probability=round(prob, 4), severity=severity,
                ))

        risk_level = "low" if pass_prob > 0.9 else ("medium" if pass_prob > 0.7 else "high")
        result = PredictedResult(
            pass_probability=pass_prob,
            defect_probabilities=defect_probs,
            risk_level=risk_level,
        )

        confidence = round(0.75 + random.uniform(0, 0.2), 4)
        needs_manual = confidence < 0.8 or pass_prob < 0.7

        prediction.set_prediction(result, confidence, model_version)
        prediction._needs_manual_inspection = needs_manual

        self._predictions[prediction.id] = prediction
        return prediction

    def identify_quality_drivers(
        self, prediction_id: str
    ) -> list[SHAPValue]:
        prediction = self._predictions.get(prediction_id)
        if not prediction:
            return []

        shap_values: list[SHAPValue] = []
        all_features = [f.name for f in prediction.input_features] + [
            "material_hardness", "ambient_temperature", "operator_skill", "equipment_age",
        ]
        base_shap = 0.5
        for i, fname in enumerate(all_features):
            sv = base_shap * math.exp(-0.3 * i) * random.uniform(0.6, 1.4)
            if random.random() < 0.4:
                sv = -sv
            shap_values.append(SHAPValue(
                feature_name=fname,
                shap_value=round(sv, 4),
            ))

        prediction.set_shap_values(shap_values)
        return prediction.shap_values

    def detect_quality_drift(
        self, prediction_id: str
    ) -> QualityDriftRecord | None:
        prediction = self._predictions.get(prediction_id)
        if not prediction:
            return None

        accuracy_drift = random.uniform(0.0, 0.2)
        drift_type = "concept_drift" if random.random() > 0.3 else "data_drift"

        record = QualityDriftRecord(
            drift_type=drift_type,
            metric_name="prediction_accuracy",
            previous_value=round(0.92, 4),
            current_value=round(0.92 - accuracy_drift, 4),
            drift_magnitude=round(accuracy_drift, 4),
        )

        if accuracy_drift > self._drift_threshold_critical:
            record.action_taken = "model_retrain_triggered"
        elif accuracy_drift > self._drift_threshold_warning:
            record.action_taken = "monitoring_increased"
        else:
            record.action_taken = "no_action"

        prediction.add_drift_record(record)
        return record

    def optimize_process_for_quality(
        self,
        prediction_id: str,
        constraints: dict[str, Any] | None = None,
    ) -> list[ProcessParameterRecommendation]:
        prediction = self._predictions.get(prediction_id)
        if not prediction:
            return []

        recommendations: list[ProcessParameterRecommendation] = []
        feature_map = {f.name: f.value for f in prediction.input_features}

        for param in _PROCESS_PARAMS:
            current = feature_map.get(param, random.uniform(50, 200))
            improvement = random.uniform(0.02, 0.12)
            direction = random.choice([-1, 1])
            recommended = current * (1 + direction * random.uniform(0.02, 0.08))

            param_constraints = (constraints or {}).get(param, {})
            min_val = param_constraints.get("min", 0)
            max_val = param_constraints.get("max", float("inf"))
            recommended = min(max(recommended, min_val), max_val)

            recommendations.append(ProcessParameterRecommendation(
                parameter_name=param,
                current_value=round(current, 2),
                recommended_value=round(recommended, 2),
                expected_improvement=round(improvement, 4),
                constraint_satisfied=min_val <= recommended <= max_val,
            ))

        prediction.set_parameter_recommendations(recommendations)
        return recommendations

    def get_prediction(self, prediction_id: str) -> QualityPrediction | None:
        return self._predictions.get(prediction_id)

    def verify_prediction(
        self,
        prediction_id: str,
        actual_quality: str,
        actual_defects: list[str] | None = None,
        verified_by: str = "",
    ) -> QualityPrediction | None:
        prediction = self._predictions.get(prediction_id)
        if not prediction:
            return None

        actual = ActualResult(
            actual_quality=actual_quality,
            actual_defects=actual_defects or [],
            verified_at=datetime.now(timezone.utc),
            verified_by=verified_by,
        )
        prediction.set_actual_result(actual)
        return prediction