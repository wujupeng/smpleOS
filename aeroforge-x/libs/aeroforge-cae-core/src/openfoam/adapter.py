from __future__ import annotations

import asyncio
import logging
import os
import signal
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from aeroforge_cae_core.openfoam.case_manager import CaseFileManager

logger = logging.getLogger(__name__)


class SolverStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SolverProcessInfo:
    pid: int | None = None
    status: SolverStatus = SolverStatus.IDLE
    start_time: float | None = None
    elapsed_seconds: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    current_iteration: int = 0
    total_iterations: int = 0


@dataclass
class JobResult:
    job_id: str
    case_dir: str
    status: SolverStatus
    residuals: list[dict[str, Any]] = field(default_factory=list)
    force_coefficients: dict[str, list[float]] = field(default_factory=dict)
    convergence_data: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class OpenFOAMAdapter:
    def __init__(
        self,
        openfoam_dir: str = "/opt/openfoam",
        working_dir: str = "/tmp/aeroforge/openfoam",
        n_proc: int = 1,
    ) -> None:
        self._openfoam_dir = Path(openfoam_dir)
        self._working_dir = Path(working_dir)
        self._n_proc = n_proc
        self._processes: dict[str, SolverProcessInfo] = {}
        self._case_manager = CaseFileManager()
        self._env = self._build_env()

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        foam_bash = self._openfoam_dir / "etc" / "bashrc"
        if foam_bash.exists():
            env["FOAM_INSTALL_DIR"] = str(self._openfoam_dir)
            env["WM_PROJECT_DIR"] = str(self._openfoam_dir)
        return env

    @property
    def case_manager(self) -> CaseFileManager:
        return self._case_manager

    async def start_solver(
        self,
        case_dir: str,
        solver: str = "simpleFoam",
        n_proc: int | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        proc_count = n_proc or self._n_proc
        case_path = Path(case_dir)

        if not case_path.exists():
            raise FileNotFoundError(f"Case directory not found: {case_dir}")

        log_file = case_path / "log.solver"
        process_info = SolverProcessInfo(status=SolverStatus.RUNNING)

        try:
            if proc_count > 1:
                cmd = f"cd {case_dir} && mpirun -np {proc_count} {solver} -parallel > {log_file} 2>&1"
            else:
                cmd = f"cd {case_dir} && {solver} > {log_file} 2>&1"

            proc = await asyncio.create_subprocess_shell(
                cmd,
                env=self._env,
                preexec_fn=os.setsid if os.name != "nt" else None,
            )
            process_info.pid = proc.pid
            self._processes[job_id] = process_info

            logger.info(
                "Started OpenFOAM solver job=%s solver=%s n_proc=%d pid=%d",
                job_id, solver, proc_count, proc.pid,
            )
        except Exception as exc:
            process_info.status = SolverStatus.FAILED
            self._processes[job_id] = process_info
            logger.error("Failed to start solver job=%s: %s", job_id, exc)
            raise

        return job_id

    async def stop_solver(self, job_id: str) -> None:
        info = self._processes.get(job_id)
        if info is None or info.pid is None:
            raise ValueError(f"Job not found or no process: {job_id}")

        try:
            if os.name != "nt":
                os.killpg(os.getpgid(info.pid), signal.SIGTERM)
            else:
                os.kill(info.pid, signal.SIGTERM)
            info.status = SolverStatus.CANCELLED
            logger.info("Stopped solver job=%s pid=%d", job_id, info.pid)
        except ProcessLookupError:
            info.status = SolverStatus.COMPLETED
            logger.info("Process already terminated job=%s", job_id)
        except Exception as exc:
            logger.error("Failed to stop solver job=%s: %s", job_id, exc)
            raise

    async def get_status(self, job_id: str) -> SolverProcessInfo:
        info = self._processes.get(job_id)
        if info is None:
            raise ValueError(f"Job not found: {job_id}")
        return info

    async def monitor_job(self, job_id: str, poll_interval: float = 5.0) -> JobResult:
        info = self._processes.get(job_id)
        if info is None:
            raise ValueError(f"Job not found: {job_id}")

        while info.status == SolverStatus.RUNNING:
            await asyncio.sleep(poll_interval)
            await self._update_process_info(job_id)

        return await self._build_job_result(job_id)

    async def _update_process_info(self, job_id: str) -> None:
        info = self._processes.get(job_id)
        if info is None or info.pid is None:
            return

        try:
            if os.name != "nt":
                os.kill(info.pid, 0)
        except ProcessLookupError:
            info.status = SolverStatus.COMPLETED
            return
        except PermissionError:
            pass

    async def _build_job_result(self, job_id: str) -> JobResult:
        info = self._processes.get(job_id)
        if info is None:
            raise ValueError(f"Job not found: {job_id}")

        return JobResult(
            job_id=job_id,
            case_dir="",
            status=info.status,
        )

    def parse_results(self, case_dir: str) -> dict[str, Any]:
        case_path = Path(case_dir)
        results: dict[str, Any] = {
            "residuals": [],
            "force_coefficients": {},
            "convergence": {},
        }

        residuals_dir = case_path / "postProcessing" / "residuals"
        if residuals_dir.exists():
            results["residuals"] = self._parse_residuals(residuals_dir)

        forces_dir = case_path / "postProcessing" / "forces"
        if forces_dir.exists():
            results["force_coefficients"] = self._parse_forces(forces_dir)

        return results

    def _parse_residuals(self, residuals_dir: Path) -> list[dict[str, Any]]:
        residuals: list[dict[str, Any]] = []
        time_dirs = sorted(residuals_dir.iterdir(), key=lambda p: float(p.name))
        for time_dir in time_dirs:
            if not time_dir.is_dir():
                continue
            data_file = time_dir / "residuals.dat"
            if not data_file.exists():
                continue
            try:
                time_val = float(time_dir.name)
                with open(data_file) as f:
                    lines = f.readlines()
                for line in lines:
                    if line.startswith("#") or not line.strip():
                        continue
                    parts = line.split()
                    if parts:
                        residuals.append({
                            "time": time_val,
                            "values": [float(v) for v in parts],
                        })
            except (ValueError, OSError):
                continue
        return residuals

    def _parse_forces(self, forces_dir: Path) -> dict[str, list[float]]:
        coefficients: dict[str, list[float]] = {}
        time_dirs = sorted(forces_dir.iterdir(), key=lambda p: float(p.name))
        for time_dir in time_dirs:
            if not time_dir.is_dir():
                continue
            for data_file in time_dir.glob("*.dat"):
                key = data_file.stem
                if key not in coefficients:
                    coefficients[key] = []
                try:
                    with open(data_file) as f:
                        for line in f:
                            if line.startswith("#") or not line.strip():
                                continue
                            parts = line.split()
                            if parts:
                                coefficients[key].append(float(parts[0]))
                except (ValueError, OSError):
                    continue
        return coefficients

    def write_case_files(
        self,
        case_dir: str,
        control_dict: dict[str, Any] | None = None,
        fv_schemes: dict[str, Any] | None = None,
        fv_solution: dict[str, Any] | None = None,
        turbulence_properties: dict[str, Any] | None = None,
    ) -> None:
        self._case_manager.create_case_structure(case_dir)
        if control_dict is not None:
            self._case_manager.write_control_dict(case_dir, control_dict)
        if fv_schemes is not None:
            self._case_manager.write_fv_schemes(case_dir, fv_schemes)
        if fv_solution is not None:
            self._case_manager.write_fv_solution(case_dir, fv_solution)
        if turbulence_properties is not None:
            self._case_manager.write_turbulence_properties(case_dir, turbulence_properties)

    async def submit_job(
        self,
        case_dir: str,
        solver: str = "simpleFoam",
        n_proc: int | None = None,
        callback: Any | None = None,
    ) -> str:
        job_id = await self.start_solver(case_dir, solver, n_proc)

        async def _monitor_and_callback() -> None:
            result = await self.monitor_job(job_id)
            result.case_dir = case_dir
            parsed = self.parse_results(case_dir)
            result.residuals = parsed.get("residuals", [])
            result.force_coefficients = parsed.get("force_coefficients", {})
            result.convergence_data = parsed.get("convergence", {})
            if callback is not None:
                await callback(result)

        asyncio.create_task(_monitor_and_callback())
        return job_id