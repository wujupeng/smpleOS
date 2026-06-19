from __future__ import annotations

import logging
from typing import Any

from .thermal_task import (
    ThermalAnalysisType,
    ThermalResultSummary,
    ThermalStatus,
    ThermalTask,
)

logger = logging.getLogger(__name__)

MAX_SAFE_TEMPERATURE_C = 120.0


class ThermalDomainService:
    def __init__(self) -> None:
        self._tasks: dict[str, ThermalTask] = {}

    def submit_analysis(
        self,
        model_id: str,
        analysis_type: ThermalAnalysisType = ThermalAnalysisType.STEADY_STATE,
        mesh_task_id: str | None = None,
    ) -> ThermalTask:
        task = ThermalTask(
            model_id=model_id,
            analysis_type=analysis_type,
            mesh_task_id=mesh_task_id,
        )
        self._tasks[task.id] = task
        logger.info("Submitted thermal analysis: task=%s model=%s", task.id, model_id)
        return task

    def run_analysis(self, task: ThermalTask) -> ThermalTask:
        task.start_running()
        task.update_progress(30.0, "solving_heat_transfer")

        total_power = sum(hs.power_watts for hs in task.heat_sources) if task.heat_sources else 100.0

        max_temp = 25.0 + total_power / 50.0
        min_temp = 25.0
        avg_temp = (max_temp + min_temp) / 2.0

        if task.coolant:
            cooling_effect = task.coolant.flow_rate_lpm * 2.0
            max_temp = max(25.0, max_temp - cooling_effect)
            avg_temp = (max_temp + min_temp) / 2.0

        task.update_progress(60.0, "extracting_temperature_field")

        max_heat_flux = total_power / 0.01 if total_power > 0 else 0.0
        max_gradient = (max_temp - min_temp) / 0.5 if max_temp > min_temp else 0.0

        overheated: list[dict[str, Any]] = []
        suggestions: list[str] = []

        if max_temp > MAX_SAFE_TEMPERATURE_C:
            overheated.append({
                "region": "battery_compartment",
                "temperature_c": round(max_temp, 1),
                "limit_c": MAX_SAFE_TEMPERATURE_C,
            })
            suggestions.append("电池舱温度过高，建议增加冷却液流量或增加散热面积")

        if max_temp > 80.0:
            suggestions.append("建议在高温区域增加隔热材料")

        if not task.coolant and total_power > 500:
            suggestions.append("热源功率较大，建议增加主动冷却系统")

        if not suggestions:
            suggestions.append("温度场分布合理，无需额外散热措施")

        task.update_progress(85.0, "generating_suggestions")

        result = ThermalResultSummary(
            max_temperature_c=round(max_temp, 1),
            min_temperature_c=round(min_temp, 1),
            avg_temperature_c=round(avg_temp, 1),
            max_heat_flux_w_m2=round(max_heat_flux, 1),
            max_thermal_gradient_c_m=round(max_gradient, 1),
            overheated_regions=overheated,
            thermal_management_suggestions=suggestions,
            convergence_status="converged",
        )

        task.complete(result)
        logger.info("Thermal analysis completed: task=%s max_temp=%.1fC overheated=%d",
                     task.id, result.max_temperature_c, len(result.overheated_regions))
        return task

    def get_task(self, task_id: str) -> ThermalTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[ThermalTask]:
        return list(self._tasks.values())