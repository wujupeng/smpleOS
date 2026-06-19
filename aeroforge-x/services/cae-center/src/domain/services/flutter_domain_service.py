from __future__ import annotations

import logging
import math
from typing import Any

from .flutter_task import (
    AerodynamicModel,
    FlutterResultSummary,
    FlutterStatus,
    FlutterTask,
    SpeedRange,
    StructuralMode,
)

logger = logging.getLogger(__name__)


class FlutterDomainService:
    def __init__(self) -> None:
        self._tasks: dict[str, FlutterTask] = {}

    def submit_analysis(
        self,
        model_id: str,
        speed_range: SpeedRange | None = None,
        aerodynamic_model: AerodynamicModel = AerodynamicModel.QUASI_STEADY,
        mesh_task_id: str | None = None,
    ) -> FlutterTask:
        task = FlutterTask(
            model_id=model_id,
            speed_range=speed_range,
            aerodynamic_model=aerodynamic_model,
            mesh_task_id=mesh_task_id,
        )
        self._tasks[task.id] = task
        logger.info("Submitted flutter analysis: task=%s model=%s", task.id, model_id)
        return task

    def extract_structural_modes(self, task: FlutterTask) -> list[StructuralMode]:
        if not task.structural_modes:
            default_modes = [
                StructuralMode(mode_number=1, natural_frequency_hz=5.2, damping_ratio=0.02, mode_shape="1st bending"),
                StructuralMode(mode_number=2, natural_frequency_hz=12.8, damping_ratio=0.015, mode_shape="1st torsion"),
                StructuralMode(mode_number=3, natural_frequency_hz=18.5, damping_ratio=0.012, mode_shape="2nd bending"),
            ]
            for mode in default_modes:
                task.add_structural_mode(mode)
        return task.structural_modes

    def compute_aeroelastic_stability(self, task: FlutterTask) -> FlutterResultSummary:
        task.start_running()
        task.update_progress(30.0, "computing_stability")

        modes = self.extract_structural_modes(task)
        speed_range = task.speed_range

        speeds = [
            speed_range.min_speed_ms + i * (speed_range.max_speed_ms - speed_range.min_speed_ms) / speed_range.speed_steps
            for i in range(speed_range.speed_steps + 1)
        ]

        damping_trend: list[dict[str, float]] = []
        frequency_trend: list[dict[str, float]] = []
        flutter_speed = 0.0
        flutter_freq = 0.0
        critical_mode = 1

        for speed in speeds:
            for mode in modes:
                q = 0.5 * 1.225 * speed * speed
                aero_damping = -q * 0.001 * (speed / 100.0)
                total_damping = mode.damping_ratio + aero_damping

                freq_shift = mode.natural_frequency_hz * (1.0 + 0.1 * q / 1e5)
                freq_shift = max(freq_shift, 0.1)

                damping_trend.append({
                    "speed_ms": round(speed, 2),
                    "damping": round(total_damping, 6),
                    "mode": mode.mode_number,
                })
                frequency_trend.append({
                    "speed_ms": round(speed, 2),
                    "frequency_hz": round(freq_shift, 4),
                    "mode": mode.mode_number,
                })

                if total_damping < 0 and flutter_speed == 0.0:
                    flutter_speed = speed
                    flutter_freq = freq_shift
                    critical_mode = mode.mode_number

        task.update_progress(70.0, "calculating_margin")

        divergence_speed = self._estimate_divergence_speed(modes, speed_range)

        flutter_margin = self._calculate_flutter_margin(flutter_speed, speed_range.max_speed_ms)

        design_speed = speed_range.max_speed_ms * 0.8
        meets_airworthiness = flutter_speed > design_speed * 1.15

        result = FlutterResultSummary(
            flutter_speed_ms=round(flutter_speed, 2),
            flutter_frequency_hz=round(flutter_freq, 4),
            flutter_margin=round(flutter_margin, 4),
            critical_mode=critical_mode,
            damping_trend=damping_trend,
            frequency_trend=frequency_trend,
            divergence_speed_ms=round(divergence_speed, 2),
            meets_airworthiness=meets_airworthiness,
        )

        task.complete(result)
        logger.info("Flutter analysis completed: task=%s Vf=%.1f m/s margin=%.2f",
                     task.id, result.flutter_speed_ms, result.flutter_margin)
        return result

    def _calculate_flutter_margin(self, flutter_speed: float, design_speed: float) -> float:
        if design_speed <= 0:
            return 0.0
        return (flutter_speed / design_speed) - 1.0

    def _estimate_divergence_speed(self, modes: list[StructuralMode], speed_range: SpeedRange) -> float:
        if not modes:
            return 0.0
        max_freq = max(m.natural_frequency_hz for m in modes)
        if max_freq <= 0:
            return 0.0
        return min(speed_range.max_speed_ms * 1.5, max_freq * 50.0)

    def post_process(self, task: FlutterTask) -> dict[str, Any]:
        if task.result_summary is None:
            return {"report": "No results available"}

        report: dict[str, Any] = {
            "task_id": task.id,
            "model_id": task.model_id,
            "flutter_speed_ms": task.result_summary.flutter_speed_ms,
            "flutter_margin": task.result_summary.flutter_margin,
            "critical_mode": task.result_summary.critical_mode,
            "meets_airworthiness": task.result_summary.meets_airworthiness,
            "recommendations": [],
        }

        if not task.result_summary.meets_airworthiness:
            report["recommendations"].append(
                "颤振速度不满足适航要求，建议增加结构刚度或调整质量分布"
            )

        if task.result_summary.flutter_margin < 0.15:
            report["recommendations"].append(
                "颤振裕度偏低，建议增加结构阻尼或优化气动外形"
            )

        return report

    def get_task(self, task_id: str) -> FlutterTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[FlutterTask]:
        return list(self._tasks.values())