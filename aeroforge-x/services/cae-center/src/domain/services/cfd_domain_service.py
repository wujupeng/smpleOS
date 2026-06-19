from __future__ import annotations

import logging
from typing import Any

from aeroforge_cae_core.openfoam.adapter import OpenFOAMAdapter
from aeroforge_cae_core.openfoam.case_manager import CaseFileManager

from .cfd_task import (
    CFDAnalysisType,
    CFDResultSummary,
    CFDStatus,
    CFDSolverType,
    CFDTask,
    FlightConditions,
    TurbulenceModel,
)

logger = logging.getLogger(__name__)


class CFDCaseConfig:
    @staticmethod
    def build_control_dict(task: CFDTask) -> dict[str, Any]:
        if task.analysis_type == CFDAnalysisType.STEADY:
            return {
                "application": task.solver_type.value,
                "startFrom": "startTime",
                "startTime": 0,
                "stopAt": "endTime",
                "endTime": 1000,
                "deltaT": 1,
                "writeControl": "timeStep",
                "writeInterval": 100,
            }
        return {
            "application": task.solver_type.value,
            "startFrom": "startTime",
            "startTime": 0,
            "stopAt": "endTime",
            "endTime": 0.5,
            "deltaT": 1e-4,
            "writeControl": "adjustableRunTime",
            "writeInterval": 0.01,
        }

    @staticmethod
    def build_fv_schemes(task: CFDTask) -> dict[str, Any]:
        if task.analysis_type == CFDAnalysisType.UNSTEADY:
            ddt_default = "Euler"
        else:
            ddt_default = "steadyState"
        return {
            "ddtSchemes": {"default": ddt_default},
            "gradSchemes": {"default": "Gauss linear"},
            "divSchemes": {
                "default": "none",
                "div(phi,U)": "bounded Gauss upwind",
                "div(phi,k)": "bounded Gauss upwind",
                "div(phi,omega)": "bounded Gauss upwind",
                "div((nuEff*dev2(T(grad(U)))))": "Gauss linear",
            },
            "laplacianSchemes": {"default": "Gauss linear corrected"},
            "interpolationSchemes": {"default": "linear"},
            "snGradSchemes": {"default": "corrected"},
        }

    @staticmethod
    def build_fv_solution(task: CFDTask) -> dict[str, Any]:
        return {
            "solvers": {
                "p": {
                    "solver": "GAMG",
                    "tolerance": 1e-06,
                    "relTol": 0.01,
                    "smoother": "GaussSeidel",
                },
                "U": {
                    "solver": "smoothSolver",
                    "smoother": "GaussSeidel",
                    "tolerance": 1e-05,
                    "relTol": 0.1,
                },
                "k": {
                    "solver": "smoothSolver",
                    "smoother": "GaussSeidel",
                    "tolerance": 1e-05,
                    "relTol": 0.1,
                },
                "omega": {
                    "solver": "smoothSolver",
                    "smoother": "GaussSeidel",
                    "tolerance": 1e-05,
                    "relTol": 0.1,
                },
            },
            "SIMPLE": {
                "nNonOrthogonalCorrectors": 0,
                "consistent": True,
                "residualControl": {
                    "p": 1e-05,
                    "U": 1e-05,
                    "k": 1e-05,
                    "omega": 1e-05,
                },
            },
            "relaxationFactors": {
                "equations": {"U": 0.7, "k": 0.7, "omega": 0.7},
                "fields": {"p": 0.3},
            },
        }

    @staticmethod
    def build_turbulence_properties(task: CFDTask) -> dict[str, Any]:
        return {
            "simulationType": "RAS",
            "RAS": {
                "model": task.turbulence_model.value,
                "turbulence": True,
                "printCoeffs": True,
            },
        }

    @staticmethod
    def build_boundary_conditions(task: CFDTask) -> dict[str, Any]:
        fc = task.flight_conditions
        u_freestream = fc.mach_number * 340.0 if fc.mach_number > 0 else 50.0
        return {
            "U": {
                "internalField": f"uniform ({u_freestream} 0 0)",
                "boundaryField": {
                    "farfield": {
                        "type": "freestreamVelocity",
                        "freestreamValue": f"uniform ({u_freestream} 0 0)",
                    },
                    "wall": {
                        "type": "noSlip",
                    },
                    "symmetry": {
                        "type": "symmetryPlane",
                    },
                },
            },
            "p": {
                "internalField": "uniform 0",
                "boundaryField": {
                    "farfield": {
                        "type": "freestreamPressure",
                        "freestreamValue": "uniform 0",
                    },
                    "wall": {
                        "type": "zeroGradient",
                    },
                    "symmetry": {
                        "type": "symmetryPlane",
                    },
                },
            },
        }


class CFDDomainService:
    def __init__(
        self,
        openfoam_adapter: OpenFOAMAdapter | None = None,
        working_dir: str = "/tmp/aeroforge/cfd",
    ) -> None:
        self._adapter = openfoam_adapter or OpenFOAMAdapter(working_dir=working_dir)
        self._case_config = CFDCaseConfig()
        self._tasks: dict[str, CFDTask] = {}

    def submit_analysis(
        self,
        model_id: str,
        analysis_type: CFDAnalysisType = CFDAnalysisType.STEADY,
        solver_type: CFDSolverType = CFDSolverType.SIMPLE_FOAM,
        turbulence_model: TurbulenceModel = TurbulenceModel.K_OMEGA_SST,
        flight_conditions: FlightConditions | None = None,
        mesh_task_id: str | None = None,
    ) -> CFDTask:
        task = CFDTask(
            model_id=model_id,
            analysis_type=analysis_type,
            solver_type=solver_type,
            turbulence_model=turbulence_model,
            flight_conditions=flight_conditions,
            mesh_task_id=mesh_task_id,
        )
        self._tasks[task.id] = task
        logger.info("Submitted CFD analysis: task=%s model=%s solver=%s",
                     task.id, model_id, solver_type.value)
        return task

    def prepare_case(self, task: CFDTask, case_dir: str) -> CFDTask:
        task.start_meshing()
        task.case_dir = case_dir

        self._adapter.write_case_files(
            case_dir,
            control_dict=self._case_config.build_control_dict(task),
            fv_schemes=self._case_config.build_fv_schemes(task),
            fv_solution=self._case_config.build_fv_solution(task),
            turbulence_properties=self._case_config.build_turbulence_properties(task),
        )

        bc = self._case_config.build_boundary_conditions(task)
        for field_name, field_config in bc.items():
            self._adapter.case_manager.write_boundary_conditions(
                case_dir, "0", field_name, field_config,
            )

        logger.info("Prepared CFD case for task %s at %s", task.id, case_dir)
        return task

    def execute_solver(self, task: CFDTask, n_proc: int = 1) -> str:
        if not task.case_dir:
            raise ValueError(f"Task {task.id} has no case directory")
        task.start_running()
        job_id = self._adapter.submit_job(
            task.case_dir,
            solver=task.solver_type.value,
            n_proc=n_proc,
        )
        logger.info("Started CFD solver: task=%s job=%s", task.id, job_id)
        return job_id

    def post_process(self, task: CFDTask) -> CFDTask:
        task.start_post_processing()

        if task.case_dir:
            parsed = self._adapter.parse_results(task.case_dir)
            residuals = parsed.get("residuals", [])
            force_coeffs = parsed.get("force_coefficients", {})

            cl = force_coeffs.get("lift", [0.0])[-1] if "lift" in force_coeffs else 0.0
            cd = force_coeffs.get("drag", [0.0])[-1] if "drag" in force_coeffs else 0.0
            cm = force_coeffs.get("moment", [0.0])[-1] if "moment" in force_coeffs else 0.0

            convergence = "converged" if residuals else "not_converged"
            ld_ratio = cl / cd if cd != 0 else 0.0

            result = CFDResultSummary(
                lift_coefficient=cl,
                drag_coefficient=cd,
                moment_coefficient=cm,
                convergence_status=convergence,
                lift_to_drag_ratio=ld_ratio,
            )
            task.complete(result)
        else:
            result = CFDResultSummary(
                convergence_status="no_results",
            )
            task.complete(result)

        logger.info("CFD post-processing completed: task=%s cl=%.4f cd=%.4f ld=%.2f",
                     task.id, result.lift_coefficient, result.drag_coefficient,
                     result.lift_to_drag_ratio)
        return task

    def link_to_design(self, task: CFDTask, design_target_ld: float = 10.0) -> dict[str, Any]:
        if task.result_summary is None:
            return {"linked": False, "reason": "No results available"}

        deviations: list[dict[str, Any]] = []
        ld = task.result_summary.lift_to_drag_ratio

        if ld < design_target_ld:
            deviations.append({
                "metric": "lift_to_drag_ratio",
                "actual": ld,
                "target": design_target_ld,
                "deviation": design_target_ld - ld,
                "suggestion": "Consider increasing wing aspect ratio or optimizing airfoil profile",
            })

        if task.result_summary.drag_coefficient > 0.05:
            deviations.append({
                "metric": "drag_coefficient",
                "actual": task.result_summary.drag_coefficient,
                "target": 0.05,
                "deviation": task.result_summary.drag_coefficient - 0.05,
                "suggestion": "Consider reducing surface roughness or optimizing fuselage shape",
            })

        return {
            "linked": True,
            "task_id": task.id,
            "model_id": task.model_id,
            "deviations": deviations,
            "meets_target": len(deviations) == 0,
        }

    def get_task(self, task_id: str) -> CFDTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[CFDTask]:
        return list(self._tasks.values())