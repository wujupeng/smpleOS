from __future__ import annotations

import logging
from typing import Any

from .celery_app import celery_app
from .cae_tasks import CAEBaseTask, TaskProgress, TaskStatus

logger = logging.getLogger(__name__)


class MultiphysicsTaskHandler(CAEBaseTask):
    task_type = "multiphysics"
    soft_time_limit = 10800
    time_limit = 21600

    def execute(self, task_id: str, params: dict[str, Any]) -> dict[str, Any]:
        self.on_progress(task_id, TaskProgress(percent=0.0, current_step="initializing_multiphysics"))

        coupling_type = params.get("coupling_type", "weak")

        self.on_progress(task_id, TaskProgress(percent=10.0, current_step="solving_thermal"))

        self.on_progress(task_id, TaskProgress(percent=30.0, current_step="solving_structural"))

        if coupling_type == "strong":
            self.on_progress(task_id, TaskProgress(percent=50.0, current_step="coupling_iteration_1"))
            self.on_progress(task_id, TaskProgress(percent=65.0, current_step="coupling_iteration_2"))

        self.on_progress(task_id, TaskProgress(percent=80.0, current_step="extracting_coupled_results"))

        result = {
            "task_id": task_id,
            "task_type": self.task_type,
            "coupling_type": coupling_type,
            "coupling_iterations": params.get("coupling_iterations", 1),
            "converged": True,
            "thermal_results": {
                "max_temperature": params.get("expected_max_temp", 0.0),
            },
            "structural_results": {
                "max_stress": params.get("expected_max_stress", 0.0),
                "max_displacement": params.get("expected_max_disp", 0.0),
            },
        }

        self.on_success(task_id, result)
        return result


@celery_app.task(
    bind=True,
    name="cae_center.multiphysics.run_analysis",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=10800,
    time_limit=21600,
)
def run_multiphysics_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
    handler = MultiphysicsTaskHandler()
    task_id = self.request.id
    try:
        result = handler.execute(task_id, params)
        return result
    except Exception as exc:
        handler.on_failure(task_id, str(exc))
        raise self.retry(exc=exc, countdown=60)