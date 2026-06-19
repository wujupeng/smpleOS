"""AeroForge-X V6.1 DatasetDriftDetectionService

Dataset drift detection for CFD training data:
KS test feature drift, concept drift, PSI index,
and NATS alert emission.

REQ-DG-005~009
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DriftType(str, Enum):
    FEATURE = "Feature"
    CONCEPT = "Concept"


@dataclass
class DriftDetectionResult:
    dataset_id: str
    reference_dataset_id: str
    drift_type: DriftType
    ks_statistic: float = 0.0
    ks_p_value: float = 1.0
    psi_value: float = 0.0
    concept_drift_magnitude: float = 0.0
    is_drift_detected: bool = False
    affected_features: list[str] = field(default_factory=list)
    recommended_action: str = ""

    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "reference_dataset_id": self.reference_dataset_id,
            "drift_type": self.drift_type.value,
            "ks_statistic": self.ks_statistic,
            "ks_p_value": self.ks_p_value,
            "psi_value": self.psi_value,
            "concept_drift_magnitude": self.concept_drift_magnitude,
            "is_drift_detected": self.is_drift_detected,
            "affected_features": self.affected_features,
            "recommended_action": self.recommended_action,
        }


@dataclass
class DriftHistoryEntry:
    entry_id: str
    dataset_id: str
    drift_type: DriftType
    is_drift_detected: bool
    detected_at: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "dataset_id": self.dataset_id,
            "drift_type": self.drift_type.value,
            "is_drift_detected": self.is_drift_detected,
            "detected_at": self.detected_at,
            "details": self.details,
        }


class DatasetDriftDetectionService:

    KS_ALPHA = 0.05
    PSI_THRESHOLD = 0.25
    CONCEPT_DRIFT_SIGMA = 2.0

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._history: list[DriftHistoryEntry] = []
        self._alerts: list[dict] = []

    def detectFeatureDrift(
        self,
        dataset_id: str,
        reference_dataset_id: str,
        reference_data: dict[str, list[float]],
        current_data: dict[str, list[float]],
        alpha: float | None = None,
    ) -> DriftDetectionResult:
        from scipy.stats import ks_2samp
        import numpy as np

        significance = alpha or self.KS_ALPHA
        affected_features = []
        max_ks_stat = 0.0
        min_p_value = 1.0

        for feature_name in reference_data:
            if feature_name not in current_data:
                continue
            ref_arr = np.array(reference_data[feature_name], dtype=float)
            cur_arr = np.array(current_data[feature_name], dtype=float)

            if len(ref_arr) < 2 or len(cur_arr) < 2:
                continue

            ks_stat, p_value = ks_2samp(ref_arr, cur_arr)
            max_ks_stat = max(max_ks_stat, ks_stat)
            min_p_value = min(min_p_value, p_value)

            if p_value < significance:
                affected_features.append(feature_name)

        is_drift = len(affected_features) > 0
        action = ""
        if is_drift:
            action = f"Retrain model: feature drift detected in {len(affected_features)} features"

        result = DriftDetectionResult(
            dataset_id=dataset_id,
            reference_dataset_id=reference_dataset_id,
            drift_type=DriftType.FEATURE,
            ks_statistic=max_ks_stat,
            ks_p_value=min_p_value,
            is_drift_detected=is_drift,
            affected_features=affected_features,
            recommended_action=action,
        )

        self._record_history(dataset_id, DriftType.FEATURE, is_drift, result.to_dict())

        if is_drift:
            self._emit_drift_alert(result)

        return result

    def detectConceptDrift(
        self,
        dataset_id: str,
        reference_dataset_id: str,
        baseline_errors: list[float],
        current_errors: list[float],
        threshold_sigma: float | None = None,
    ) -> DriftDetectionResult:
        import numpy as np

        sigma = threshold_sigma or self.CONCEPT_DRIFT_SIGMA
        baseline_arr = np.array(baseline_errors, dtype=float)
        current_arr = np.array(current_errors, dtype=float)

        if len(baseline_arr) == 0 or len(current_arr) == 0:
            return DriftDetectionResult(
                dataset_id=dataset_id,
                reference_dataset_id=reference_dataset_id,
                drift_type=DriftType.CONCEPT,
            )

        baseline_mean = float(np.mean(baseline_arr))
        baseline_std = float(np.std(baseline_arr))
        current_mean = float(np.mean(current_arr))

        if baseline_std == 0:
            magnitude = abs(current_mean - baseline_mean)
        else:
            magnitude = abs(current_mean - baseline_mean) / baseline_std

        is_drift = magnitude > sigma
        action = ""
        if is_drift:
            action = f"Investigate concept drift: error magnitude {magnitude:.2f}σ exceeds threshold {sigma}σ"

        result = DriftDetectionResult(
            dataset_id=dataset_id,
            reference_dataset_id=reference_dataset_id,
            drift_type=DriftType.CONCEPT,
            concept_drift_magnitude=magnitude,
            is_drift_detected=is_drift,
            recommended_action=action,
        )

        self._record_history(dataset_id, DriftType.CONCEPT, is_drift, result.to_dict())

        if is_drift:
            self._emit_drift_alert(result)

        return result

    def computePSI(
        self,
        dataset_id: str,
        reference_dataset_id: str,
        reference_data: dict[str, list[float]],
        current_data: dict[str, list[float]],
        n_bins: int = 10,
    ) -> DriftDetectionResult:
        import numpy as np

        max_psi = 0.0
        affected_features = []

        for feature_name in reference_data:
            if feature_name not in current_data:
                continue
            ref_arr = np.array(reference_data[feature_name], dtype=float)
            cur_arr = np.array(current_data[feature_name], dtype=float)

            if len(ref_arr) < 2 or len(cur_arr) < 2:
                continue

            all_values = np.concatenate([ref_arr, cur_arr])
            bins = np.linspace(np.min(all_values), np.max(all_values), n_bins + 1)

            ref_hist, _ = np.histogram(ref_arr, bins=bins)
            cur_hist, _ = np.histogram(cur_arr, bins=bins)

            ref_pct = ref_hist / len(ref_arr)
            cur_pct = cur_hist / len(cur_arr)

            psi_val = 0.0
            for i in range(len(ref_pct)):
                r = max(ref_pct[i], 1e-6)
                c = max(cur_pct[i], 1e-6)
                psi_val += (c - r) * np.log(c / r)

            max_psi = max(max_psi, psi_val)
            if psi_val > self.PSI_THRESHOLD:
                affected_features.append(feature_name)

        is_drift = len(affected_features) > 0
        action = ""
        if is_drift:
            action = f"Significant distribution shift: PSI>{self.PSI_THRESHOLD} in {len(affected_features)} features"

        result = DriftDetectionResult(
            dataset_id=dataset_id,
            reference_dataset_id=reference_dataset_id,
            drift_type=DriftType.FEATURE,
            psi_value=max_psi,
            is_drift_detected=is_drift,
            affected_features=affected_features,
            recommended_action=action,
        )

        self._record_history(dataset_id, DriftType.FEATURE, is_drift, result.to_dict())

        if is_drift:
            self._emit_drift_alert(result)

        return result

    def _emit_drift_alert(self, result: DriftDetectionResult) -> None:
        alert = {
            "subject": "aeroforge.v6.dataset.drift.detected",
            "dataset_id": result.dataset_id,
            "drift_type": result.drift_type.value,
            "is_drift_detected": result.is_drift_detected,
            "affected_features": result.affected_features,
            "recommended_action": result.recommended_action,
        }
        self._alerts.append(alert)

    def _record_history(
        self, dataset_id: str, drift_type: DriftType, is_drift: bool, details: dict
    ) -> None:
        entry = DriftHistoryEntry(
            entry_id=f"DRH-{uuid.uuid4().hex[:8]}",
            dataset_id=dataset_id,
            drift_type=drift_type,
            is_drift_detected=is_drift,
            details=details,
        )
        self._history.append(entry)

    def getDriftHistory(
        self, dataset_id: str, limit: int = 100
    ) -> list[DriftHistoryEntry]:
        entries = [e for e in self._history if e.dataset_id == dataset_id]
        return entries[-limit:]

    def getAlerts(self) -> list[dict]:
        return list(self._alerts)