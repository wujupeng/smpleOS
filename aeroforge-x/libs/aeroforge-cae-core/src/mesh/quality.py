from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QualityThresholds:
    orthogonality_min: float = 0.1
    skewness_max: float = 0.8
    aspect_ratio_max: float = 100.0
    non_orthogonal_warning: float = 70.0
    highly_skewed_warning: float = 0.5


@dataclass
class QualityReport:
    total_cells: int = 0
    passed: bool = True
    orthogonality_min: float = 0.0
    orthogonality_max: float = 0.0
    orthogonality_avg: float = 0.0
    skewness_min: float = 0.0
    skewness_max: float = 0.0
    skewness_avg: float = 0.0
    aspect_ratio_min: float = 0.0
    aspect_ratio_max: float = 0.0
    aspect_ratio_avg: float = 0.0
    non_orthogonal_count: int = 0
    non_orthogonal_percent: float = 0.0
    highly_skewed_count: int = 0
    highly_skewed_percent: float = 0.0
    warnings: list[str] = None
    errors: list[str] = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []


class MeshQualityChecker:
    def __init__(self, thresholds: QualityThresholds | None = None) -> None:
        self._thresholds = thresholds or QualityThresholds()

    def check_quality(self, metrics: dict[str, Any]) -> QualityReport:
        report = QualityReport(
            total_cells=metrics.get("total_cells", 0),
            orthogonality_min=metrics.get("orthogonality_min", 0.0),
            orthogonality_max=metrics.get("orthogonality_max", 0.0),
            orthogonality_avg=metrics.get("orthogonality_avg", 0.0),
            skewness_min=metrics.get("skewness_min", 0.0),
            skewness_max=metrics.get("skewness_max", 0.0),
            skewness_avg=metrics.get("skewness_avg", 0.0),
            aspect_ratio_min=metrics.get("aspect_ratio_min", 0.0),
            aspect_ratio_max=metrics.get("aspect_ratio_max", 0.0),
            aspect_ratio_avg=metrics.get("aspect_ratio_avg", 0.0),
            non_orthogonal_count=metrics.get("non_orthogonal_count", 0),
            highly_skewed_count=metrics.get("highly_skewed_count", 0),
        )

        if report.total_cells > 0:
            report.non_orthogonal_percent = round(
                report.non_orthogonal_count / report.total_cells * 100, 2
            )
            report.highly_skewed_percent = round(
                report.highly_skewed_count / report.total_cells * 100, 2
            )

        self._evaluate_thresholds(report)
        logger.info(
            "Mesh quality check: passed=%s ortho_min=%.2f skew_max=%.2f ar_max=%.1f",
            report.passed, report.orthogonality_min, report.skewness_max, report.aspect_ratio_max,
        )
        return report

    def check_openfoam_mesh(self, case_dir: str) -> QualityReport:
        metrics = self._parse_openfoam_check_mesh(case_dir)
        return self.check_quality(metrics)

    def _evaluate_thresholds(self, report: QualityReport) -> None:
        report.passed = True

        if report.orthogonality_min < self._thresholds.orthogonality_min:
            report.errors.append(
                f"Minimum orthogonality {report.orthogonality_min:.2f} "
                f"below threshold {self._thresholds.orthogonality_min:.2f}"
            )
            report.passed = False

        if report.skewness_max > self._thresholds.skewness_max:
            report.errors.append(
                f"Maximum skewness {report.skewness_max:.2f} "
                f"exceeds threshold {self._thresholds.skewness_max:.2f}"
            )
            report.passed = False

        if report.aspect_ratio_max > self._thresholds.aspect_ratio_max:
            report.warnings.append(
                f"Maximum aspect ratio {report.aspect_ratio_max:.1f} "
                f"exceeds threshold {self._thresholds.aspect_ratio_max:.1f}"
            )

        if report.non_orthogonal_percent > self._thresholds.non_orthogonal_warning:
            report.warnings.append(
                f"Non-orthogonal cells {report.non_orthogonal_percent:.1f}% "
                f"exceeds warning level {self._thresholds.non_orthogonal_warning:.1f}%"
            )

        if report.highly_skewed_percent > self._thresholds.highly_skewed_warning:
            report.warnings.append(
                f"Highly skewed cells {report.highly_skewed_percent:.1f}% "
                f"exceeds warning level {self._thresholds.highly_skewed_warning:.1f}%"
            )

    @staticmethod
    def _parse_openfoam_check_mesh(case_dir: str) -> dict[str, Any]:
        return {
            "total_cells": 0,
            "orthogonality_min": 1.0,
            "orthogonality_max": 1.0,
            "orthogonality_avg": 1.0,
            "skewness_min": 0.0,
            "skewness_max": 0.0,
            "skewness_avg": 0.0,
            "aspect_ratio_min": 1.0,
            "aspect_ratio_max": 1.0,
            "aspect_ratio_avg": 1.0,
            "non_orthogonal_count": 0,
            "highly_skewed_count": 0,
        }

    def get_quality_summary(self, report: QualityReport) -> dict[str, Any]:
        return {
            "passed": report.passed,
            "total_cells": report.total_cells,
            "orthogonality": {
                "min": report.orthogonality_min,
                "max": report.orthogonality_max,
                "avg": report.orthogonality_avg,
            },
            "skewness": {
                "min": report.skewness_min,
                "max": report.skewness_max,
                "avg": report.skewness_avg,
            },
            "aspect_ratio": {
                "min": report.aspect_ratio_min,
                "max": report.aspect_ratio_max,
                "avg": report.aspect_ratio_avg,
            },
            "non_orthogonal_percent": report.non_orthogonal_percent,
            "highly_skewed_percent": report.highly_skewed_percent,
            "warnings": report.warnings,
            "errors": report.errors,
        }