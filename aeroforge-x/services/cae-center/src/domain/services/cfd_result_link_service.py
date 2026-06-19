from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from aeroforge_common.domain.base import DomainEvent

logger = logging.getLogger(__name__)


@dataclass
class DesignDeviation:
    metric: str
    actual: float
    target: float
    deviation: float
    suggestion: str


@dataclass
class CFDAnalysisResult:
    task_id: str
    model_id: str
    lift_coefficient: float = 0.0
    drag_coefficient: float = 0.0
    moment_coefficient: float = 0.0
    lift_to_drag_ratio: float = 0.0
    convergence_status: str = "not_converged"
    deviations: list[DesignDeviation] = field(default_factory=list)


class CFDResultLinkService:
    DESIGN_TARGETS: dict[str, dict[str, float]] = {
        "fixed_wing": {"ld_ratio": 12.0, "cd_max": 0.04},
        "evtol": {"ld_ratio": 8.0, "cd_max": 0.06},
        "glider": {"ld_ratio": 20.0, "cd_max": 0.02},
        "uav": {"ld_ratio": 10.0, "cd_max": 0.05},
    }

    def __init__(self) -> None:
        self._analysis_results: dict[str, CFDAnalysisResult] = {}

    def process_completed_event(self, event: DomainEvent) -> CFDAnalysisResult | None:
        if event.event_type != "cae.analysis.completed":
            return None

        payload = event.payload
        if payload.get("task_type") != "cfd":
            return None

        result_summary = payload.get("result_summary", {})
        result = CFDAnalysisResult(
            task_id=payload.get("task_id", ""),
            model_id=payload.get("model_id", ""),
            lift_coefficient=result_summary.get("lift_coefficient", 0.0),
            drag_coefficient=result_summary.get("drag_coefficient", 0.0),
            moment_coefficient=result_summary.get("moment_coefficient", 0.0),
            lift_to_drag_ratio=result_summary.get("lift_to_drag_ratio", 0.0),
            convergence_status=result_summary.get("convergence_status", "unknown"),
        )

        self._check_deviations(result)
        self._analysis_results[result.task_id] = result

        logger.info(
            "Processed CFD result: task=%s model=%s ld=%.2f deviations=%d",
            result.task_id, result.model_id, result.lift_to_drag_ratio,
            len(result.deviations),
        )
        return result

    def _check_deviations(self, result: CFDAnalysisResult) -> None:
        targets = self.DESIGN_TARGETS.get("fixed_wing", {})

        ld_target = targets.get("ld_ratio", 10.0)
        if result.lift_to_drag_ratio < ld_target:
            result.deviations.append(DesignDeviation(
                metric="lift_to_drag_ratio",
                actual=result.lift_to_drag_ratio,
                target=ld_target,
                deviation=ld_target - result.lift_to_drag_ratio,
                suggestion="升阻比低于设计目标，建议增加机翼展弦比或优化翼型剖面",
            ))

        cd_max = targets.get("cd_max", 0.05)
        if result.drag_coefficient > cd_max:
            result.deviations.append(DesignDeviation(
                metric="drag_coefficient",
                actual=result.drag_coefficient,
                target=cd_max,
                deviation=result.drag_coefficient - cd_max,
                suggestion="阻力系数超标，建议优化机身外形或减少表面粗糙度",
            ))

    def get_result(self, task_id: str) -> CFDAnalysisResult | None:
        return self._analysis_results.get(task_id)

    def get_model_analysis_status(self, model_id: str) -> dict[str, Any]:
        for result in self._analysis_results.values():
            if result.model_id == model_id:
                return {
                    "model_id": model_id,
                    "analysis_completed": True,
                    "last_cfd_task_id": result.task_id,
                    "lift_to_drag_ratio": result.lift_to_drag_ratio,
                    "convergence_status": result.convergence_status,
                    "has_deviations": len(result.deviations) > 0,
                    "deviation_count": len(result.deviations),
                    "deviations": [
                        {
                            "metric": d.metric,
                            "actual": d.actual,
                            "target": d.target,
                            "suggestion": d.suggestion,
                        }
                        for d in result.deviations
                    ],
                }
        return {"model_id": model_id, "analysis_completed": False}