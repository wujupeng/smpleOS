from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FEniCSStatus(str, Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    SOLVING = "solving"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FEniCSJobResult:
    job_id: str
    status: FEniCSStatus
    problem_type: str
    mesh_path: str | None = None
    results: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    solve_time_seconds: float = 0.0
    dof_count: int = 0


class FEniCSAdapter:
    def __init__(
        self,
        working_dir: str = "/tmp/aeroforge/fenics",
    ) -> None:
        self._working_dir = Path(working_dir)
        self._working_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, dict[str, Any]] = {}

    async def solve(
        self,
        problem_config: dict[str, Any],
        mesh_path: str | None = None,
        callback: Any | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        job_dir = self._working_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        job_info: dict[str, Any] = {
            "job_id": job_id,
            "status": FEniCSStatus.PREPARING,
            "problem_config": problem_config,
            "mesh_path": mesh_path,
            "job_dir": str(job_dir),
            "result": None,
        }
        self._jobs[job_id] = job_info

        logger.info("Created FEniCS job %s for problem type=%s",
                     job_id, problem_config.get("problem_type", "unknown"))

        return job_id

    async def get_status(self, job_id: str) -> FEniCSStatus:
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        return job["status"]

    async def get_result(self, job_id: str) -> FEniCSJobResult:
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        result = job.get("result")
        if result is None:
            return FEniCSJobResult(
                job_id=job_id,
                status=job["status"],
                problem_type=job["problem_config"].get("problem_type", "unknown"),
            )
        return result

    async def cancel(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        if job["status"] in (FEniCSStatus.COMPLETED, FEniCSStatus.FAILED):
            raise ValueError(f"Cannot cancel job in state {job['status']}")
        job["status"] = FEniCSStatus.CANCELLED
        logger.info("Cancelled FEniCS job %s", job_id)

    async def list_jobs(self) -> list[str]:
        return list(self._jobs.keys())

    def _update_job_status(self, job_id: str, status: FEniCSStatus) -> None:
        job = self._jobs.get(job_id)
        if job is not None:
            job["status"] = status