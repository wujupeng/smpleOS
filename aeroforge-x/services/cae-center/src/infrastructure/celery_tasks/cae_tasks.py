from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskPriority(int, Enum):
    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    PROGRESS = "progress"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


@dataclass
class TaskProgress:
    percent: float = 0.0
    current_step: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskCallback:
    event_type: str
    task_id: str
    status: TaskStatus
    progress: TaskProgress | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class CAEBaseTask(ABC):
    task_type: str = "base"
    max_retries: int = 3
    retry_delay_seconds: int = 60
    soft_time_limit: int = 3600
    time_limit: int = 7200

    @abstractmethod
    def execute(self, task_id: str, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def on_progress(self, task_id: str, progress: TaskProgress) -> None:
        logger.info("Task %s progress: %.1f%% - %s", task_id, progress.percent, progress.current_step)
        self._publish_status_change(task_id, TaskStatus.PROGRESS, progress=progress)

    def on_success(self, task_id: str, result: dict[str, Any]) -> None:
        logger.info("Task %s completed successfully", task_id)
        self._publish_status_change(task_id, TaskStatus.SUCCESS, result=result)

    def on_failure(self, task_id: str, error: str) -> None:
        logger.error("Task %s failed: %s", task_id, error)
        self._publish_status_change(task_id, TaskStatus.FAILURE, error=error)

    def on_retry(self, task_id: str, attempt: int, error: str) -> None:
        logger.warning("Task %s retry attempt %d: %s", task_id, attempt, error)
        self._publish_status_change(task_id, TaskStatus.RETRY, error=error)

    def _publish_status_change(
        self,
        task_id: str,
        status: TaskStatus,
        progress: TaskProgress | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        callback = TaskCallback(
            event_type="cae.task.status_changed",
            task_id=task_id,
            status=status,
            progress=progress,
            result=result,
            error=error,
        )
        logger.debug("Publishing status change: %s", callback)