from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QualityMetrics:
    completeness: float = 0.0
    consistency: float = 0.0
    timeliness: float = 0.0
    connectivity: float = 0.0
    coverage: float = 0.0
    freshness: float = 0.0

    @property
    def overall_score(self) -> float:
        weights = {
            "completeness": 0.2,
            "consistency": 0.25,
            "timeliness": 0.15,
            "connectivity": 0.15,
            "coverage": 0.15,
            "freshness": 0.1,
        }
        return round(
            sum(getattr(self, k) * w for k, w in weights.items()),
            4,
        )

    def to_dict(self) -> dict:
        return {
            "completeness": self.completeness,
            "consistency": self.consistency,
            "timeliness": self.timeliness,
            "connectivity": self.connectivity,
            "coverage": self.coverage,
            "freshness": self.freshness,
            "overall_score": self.overall_score,
        }