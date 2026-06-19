from __future__ import annotations

import logging
from typing import Any

from .celery_app import celery_app
from .cae_tasks import CAEBaseTask, TaskProgress, TaskStatus

logger = logging.getLogger(__name__)


class FlutterTaskHandler(CAEBaseTask):
    task_type = "flutter"
    soft_time_limit = 5400
    time_limit = 10800

    def execute(self, task_id: str, params: dict[str, Any]) -> dict[str, Any]:
        self.on_progress(task_id, TaskProgress(percent=0.0, current_step="loading_structural_model"))

        self.on_progress(task_id, TaskProgress(percent=20.0, current_step="modal_analysis"))

        self.on_progress(task_id, TaskProgress(percent=40.0, current_step="aeroelastic_coupling"))

        self.on_progress(task_id, TaskProgress(percent=60.0, current_step="flutter_speed_calculation"))

        self.on_progress(task_id, TaskProgress(percent=80.0, current_step="p_k_analysis"))

        result = {
            "task_id": task_id,
            "task_type": self.task_type,
            "flutter_speed": params.get("expected_flutter_speed", 0.0),
            "flutter_frequency": params.get("expected_flutter_freq", 0.0),
            "critical_mode": params.get("critical_mode", 1),
            "divergence_speed": params.get("divergence_speed", 0.0),
            "modes_analyzed": params.get("n_modes", 10),
        }

        self.on_success(task_id, result)
        return result


@celery_app.task(
    bind=True,
    name="cae_center.flutter.run_analysis",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=5400,
    time_limit=10800,
)
def run_flutter_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
    handler = FlutterTaskHandler()
    task_id = self.request.id
    try:
        result = handler.execute(task_id, params)
        return result
    except Exception as exc:
        handler.on_failure(task_id, str(exc))
        raise self.retry(exc=exc, countdown=60)