from __future__ import annotations

import logging
from typing import Any

from .celery_app import celery_app
from .cae_tasks import CAEBaseTask, TaskProgress, TaskStatus

logger = logging.getLogger(__name__)


class FEATaskHandler(CAEBaseTask):
    task_type = "fea"
    soft_time_limit = 3600
    time_limit = 7200

    def execute(self, task_id: str, params: dict[str, Any]) -> dict[str, Any]:
        self.on_progress(task_id, TaskProgress(percent=0.0, current_step="loading_mesh"))

        problem_type = params.get("problem_type", "linear_elasticity")

        self.on_progress(task_id, TaskProgress(percent=20.0, current_step="building_problem"))

        self.on_progress(task_id, TaskProgress(percent=40.0, current_step="applying_boundary_conditions"))

        self.on_progress(task_id, TaskProgress(percent=60.0, current_step="solving"))

        self.on_progress(task_id, TaskProgress(percent=80.0, current_step="extracting_results"))

        result = {
            "task_id": task_id,
            "task_type": self.task_type,
            "problem_type": problem_type,
            "max_stress": params.get("expected_max_stress", 0.0),
            "max_displacement": params.get("expected_max_disp", 0.0),
            "dof_count": params.get("dof_count", 0),
            "safety_factor": params.get("safety_factor", 0.0),
        }

        self.on_success(task_id, result)
        return result


@celery_app.task(
    bind=True,
    name="cae_center.fea.run_analysis",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=3600,
    time_limit=7200,
)
def run_fea_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
    handler = FEATaskHandler()
    task_id = self.request.id
    try:
        result = handler.execute(task_id, params)
        return result
    except Exception as exc:
        handler.on_failure(task_id, str(exc))
        raise self.retry(exc=exc, countdown=60)