"""AeroForge-X V6.1 DatasetQualityScoreService

Dataset quality scoring with four dimensions (0-100):
Completeness, Consistency, Timeliness, Representativeness.
Quality degradation alerts and UQ uncertainty inflation.

REQ-DG-010~013
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


QUALITY_THRESHOLD = 70.0
INFLATION_SCALE = 0.5

WEIGHTS = {
    "completeness": 0.25,
    "consistency": 0.25,
    "timeliness": 0.25,
    "representativeness": 0.25,
}


@dataclass
class DatasetQualityAssessment:
    assessment_id: str
    dataset_id: str
    overall_score: float = 0.0
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    timeliness_score: float = 0.0
    representativeness_score: float = 0.0
    improvement_recommendations: str = ""
    assessed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "assessment_id": self.assessment_id,
            "dataset_id": self.dataset_id,
            "overall_score": round(self.overall_score, 2),
            "completeness_score": round(self.completeness_score, 2),
            "consistency_score": round(self.consistency_score, 2),
            "timeliness_score": round(self.timeliness_score, 2),
            "representativeness_score": round(self.representativeness_score, 2),
            "improvement_recommendations": self.improvement_recommendations,
            "assessed_at": self.assessed_at,
        }


class DatasetQualityScoreService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._assessments: dict[str, list[DatasetQualityAssessment]] = {}
        self._alerts: list[dict] = []

    def computeQualityScore(
        self,
        dataset_id: str,
        missing_value_ratio: float = 0.0,
        constraint_violation_ratio: float = 0.0,
        data_age_days: float = 0.0,
        max_acceptable_age_days: float = 365.0,
        design_space_coverage: float = 1.0,
    ) -> DatasetQualityAssessment:
        completeness = max(0.0, (1.0 - missing_value_ratio) * 100.0)
        consistency = max(0.0, (1.0 - constraint_violation_ratio) * 100.0)
        timeliness = max(0.0, 100.0 - (data_age_days / max_acceptable_age_days) * 100.0)
        representativeness = min(100.0, design_space_coverage * 100.0)

        overall = (
            completeness * WEIGHTS["completeness"]
            + consistency * WEIGHTS["consistency"]
            + timeliness * WEIGHTS["timeliness"]
            + representativeness * WEIGHTS["representativeness"]
        )

        recommendations = []
        if completeness < 80:
            recommendations.append("Improve data completeness: reduce missing values")
        if consistency < 80:
            recommendations.append("Improve data consistency: fix constraint violations")
        if timeliness < 80:
            recommendations.append("Improve data timeliness: refresh stale data")
        if representativeness < 80:
            recommendations.append("Improve data representativeness: expand design space coverage")

        assessment = DatasetQualityAssessment(
            assessment_id=f"DQA-{uuid.uuid4().hex[:8]}",
            dataset_id=dataset_id,
            overall_score=overall,
            completeness_score=completeness,
            consistency_score=consistency,
            timeliness_score=timeliness,
            representativeness_score=representativeness,
            improvement_recommendations="; ".join(recommendations),
        )

        if dataset_id not in self._assessments:
            self._assessments[dataset_id] = []
        self._assessments[dataset_id].append(assessment)

        if overall < QUALITY_THRESHOLD:
            self._emit_quality_alert(assessment)

        return assessment

    def inflateUQUncertainty(
        self, base_uncertainty: float, quality_score: float
    ) -> float:
        if quality_score >= QUALITY_THRESHOLD:
            return base_uncertainty

        inflation_factor = 1.0 + max(0.0, (QUALITY_THRESHOLD - quality_score) / QUALITY_THRESHOLD) * INFLATION_SCALE
        return base_uncertainty * inflation_factor

    def _emit_quality_alert(self, assessment: DatasetQualityAssessment) -> None:
        alert = {
            "subject": "aeroforge.v6.dataset.quality.degraded",
            "dataset_id": assessment.dataset_id,
            "quality_score": assessment.overall_score,
            "completeness_score": assessment.completeness_score,
            "consistency_score": assessment.consistency_score,
            "timeliness_score": assessment.timeliness_score,
            "representativeness_score": assessment.representativeness_score,
            "improvement_recommendations": assessment.improvement_recommendations,
        }
        self._alerts.append(alert)

    def getAssessments(
        self, dataset_id: str, limit: int = 100
    ) -> list[DatasetQualityAssessment]:
        entries = self._assessments.get(dataset_id, [])
        return entries[-limit:]

    def getLatestAssessment(self, dataset_id: str) -> Optional[DatasetQualityAssessment]:
        entries = self._assessments.get(dataset_id, [])
        return entries[-1] if entries else None

    def getAlerts(self) -> list[dict]:
        return list(self._alerts)