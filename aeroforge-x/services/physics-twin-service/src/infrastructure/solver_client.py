import os
from typing import Any


class SolverClient:
    def __init__(self):
        self._openfoam_endpoint = os.getenv("OPENFOAM_ENDPOINT", "http://localhost:8080/openfoam")
        self._fenics_endpoint = os.getenv("FENICS_ENDPOINT", "http://localhost:8081/fenics")

    async def submit_openfoam(self, simulation_config: dict[str, Any]) -> str:
        return f"openfoam-job-{simulation_config.get('simulation_id', 'unknown')}"

    async def submit_fenics(self, simulation_config: dict[str, Any]) -> str:
        return f"fenics-job-{simulation_config.get('simulation_id', 'unknown')}"

    async def get_job_status(self, solver_type: str, job_id: str) -> str:
        return "Running"

    async def cancel_job(self, solver_type: str, job_id: str) -> None:
        pass

    async def get_job_results(self, solver_type: str, job_id: str) -> dict[str, Any]:
        return {"scalar_results": {}, "convergence_history": {}}


solver_client = SolverClient()