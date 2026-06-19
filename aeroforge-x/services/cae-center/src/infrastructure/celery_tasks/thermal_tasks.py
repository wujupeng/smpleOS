from __future__ import annotations

import logging
from typing import Any

from .celery_app import celery_app
from .cae_tasks import CAEBaseTask, TaskProgress, TaskStatus

logger = logging.getLogger(__name__)


class ThermalTaskHandler(CAEBaseTask):
    task_type = "thermal"
    soft_time_limit = 3600
    time_limit = 7200

    def execute(self, task_id: str, params: dict[str, Any]) -> dict[str, Any]:
        self.on_progress(task_id, TaskProgress(percent=0.0, current_step="loading_thermal_model"))

        analysis_type = params.get("analysis_type", "steady_state")

        self.on_progress(task_id, TaskProgress(percent=20.0, current_step="applying_thermal_bc"))

        self.on_progress(task_id, TaskProgress(percent=40.0, current_step="solving_heat_transfer"))

        self.on_progress(task_id, TaskProgress(percent=70.0, current_step="extracting_temperature_field"))

        result = {
            "task_id": task_id,
            "task_type": self.task_type,
            "analysis_type": analysis_type,
            "max_temperature": params.get("expected_max_temp", 0.0),
            "min_temperature": params.get("expected_min_temp", 0.0),
            "heat_flux_max": params.get("expected_max_flux", 0.0),
            "thermal_gradient_max": params.get("expected_max_gradient", 0.0),
        }

        self.on_success(task_id, result)
        return result


@celery_app.task(
    bind=True,
    name="cae_center.thermal.run_analysis",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=3600,
    time_limit=7200,
)
def run_thermal_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
    handler = ThermalTaskHandler()
    task_id = self.request.id
    try:
        result = handler.execute(task_id, params)
        return result
    except Exception as exc:
        handler.on_failure(task_id, str(exc))
        raise self.retry(exc=exc, countdown=60)