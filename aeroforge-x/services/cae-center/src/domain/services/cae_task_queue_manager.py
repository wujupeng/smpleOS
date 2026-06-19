from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskPriority(int, Enum):
    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskType(str, Enum):
    CFD = "cfd"
    FEA = "fea"
    FLUTTER = "flutter"
    THERMAL = "thermal"
    MULTIPHYSICS = "multiphysics"
    MESH = "mesh"


@dataclass
class QueueEntry:
    task_id: str
    task_type: TaskType
    priority: TaskPriority
    submitted_at: datetime
    resource_requirements: dict[str, Any] = field(default_factory=dict)
    estimated_duration_seconds: float = 0.0
    status: str = "queued"


@dataclass
class ResourceStatus:
    total_workers: int = 0
    active_workers: int = 0
    total_tasks_running: int = 0
    total_tasks_queued: int = 0
    available_slots: dict[str, int] = field(default_factory=dict)


class CAETaskQueueManager:
    RESOURCE_MAP: dict[TaskType, str] = {
        TaskType.CFD: "cfd",
        TaskType.FEA: "fea",
        TaskType.FLUTTER: "flutter",
        TaskType.THERMAL: "thermal",
        TaskType.MULTIPHYSICS: "multiphysics",
        TaskType.MESH: "mesh",
    }

    DURATION_ESTIMATES: dict[TaskType, float] = {
        TaskType.CFD: 3600.0,
        TaskType.FEA: 1800.0,
        TaskType.FLUTTER: 2700.0,
        TaskType.THERMAL: 1800.0,
        TaskType.MULTIPHYSICS: 5400.0,
        TaskType.MESH: 900.0,
    }

    def __init__(self) -> None:
        self._queue: list[QueueEntry] = []
        self._history: list[dict[str, Any]] = []

    def enqueue(
        self,
        task_id: str,
        task_type: TaskType,
        priority: TaskPriority = TaskPriority.NORMAL,
        resource_requirements: dict[str, Any] | None = None,
    ) -> QueueEntry:
        entry = QueueEntry(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            submitted_at=datetime.now(timezone.utc),
            resource_requirements=resource_requirements or {},
            estimated_duration_seconds=self.DURATION_ESTIMATES.get(task_type, 1800.0),
        )
        self._queue.append(entry)
        self._queue.sort(key=lambda e: e.priority.value)
        logger.info("Enqueued task %s type=%s priority=%s", task_id, task_type.value, priority.name)
        return entry

    def prioritize(self, task_id: str, new_priority: TaskPriority) -> QueueEntry | None:
        for entry in self._queue:
            if entry.task_id == task_id:
                entry.priority = new_priority
                self._queue.sort(key=lambda e: e.priority.value)
                logger.info("Updated task %s priority to %s", task_id, new_priority.name)
                return entry
        return None

    def estimate_completion(self, task_id: str) -> dict[str, Any] | None:
        entry = self._get_entry(task_id)
        if entry is None:
            return None

        position = self._queue.index(entry)
        wait_time = sum(
            e.estimated_duration_seconds for e in self._queue[:position]
        )
        estimated_start = datetime.now(timezone.utc).timestamp() + wait_time
        estimated_end = estimated_start + entry.estimated_duration_seconds

        return {
            "task_id": task_id,
            "queue_position": position,
            "estimated_wait_seconds": round(wait_time, 0),
            "estimated_start": datetime.fromtimestamp(estimated_start, tz=timezone.utc).isoformat(),
            "estimated_end": datetime.fromtimestamp(estimated_end, tz=timezone.utc).isoformat(),
            "estimated_duration_seconds": entry.estimated_duration_seconds,
        }

    def get_resource_status(self) -> ResourceStatus:
        return ResourceStatus(
            total_workers=5,
            active_workers=5,
            total_tasks_running=sum(1 for e in self._queue if e.status == "running"),
            total_tasks_queued=sum(1 for e in self._queue if e.status == "queued"),
            available_slots={
                "cfd": 2,
                "fea": 2,
                "flutter": 1,
                "thermal": 2,
                "multiphysics": 1,
            },
        )

    def schedule_task(self, task_id: str) -> dict[str, Any] | None:
        entry = self._get_entry(task_id)
        if entry is None:
            return None

        resource_key = self.RESOURCE_MAP.get(entry.task_type, "default")
        status = self.get_resource_status()
        available = status.available_slots.get(resource_key, 0)

        if available > 0:
            entry.status = "scheduled"
            return {
                "task_id": task_id,
                "status": "scheduled",
                "assigned_resource": resource_key,
            }
        return {
            "task_id": task_id,
            "status": "waiting",
            "reason": f"No available {resource_key} workers",
        }

    def get_queue(self) -> list[dict[str, Any]]:
        return [
            {
                "task_id": e.task_id,
                "task_type": e.task_type.value,
                "priority": e.priority.name,
                "status": e.status,
                "submitted_at": e.submitted_at.isoformat(),
                "estimated_duration_seconds": e.estimated_duration_seconds,
            }
            for e in self._queue
        ]

    def remove(self, task_id: str) -> bool:
        entry = self._get_entry(task_id)
        if entry is not None:
            self._queue.remove(entry)
            self._history.append({"task_id": task_id, "removed_at": datetime.now(timezone.utc).isoformat()})
            return True
        return False

    def _get_entry(self, task_id: str) -> QueueEntry | None:
        for entry in self._queue:
            if entry.task_id == task_id:
                return entry
        return None