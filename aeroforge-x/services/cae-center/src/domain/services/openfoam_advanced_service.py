from __future__ import annotations

import math
import uuid
from typing import Any

from .entities.openfoam_advanced import (
    ParametricStudy, SweepRange, CaseResult, ParametricStudyStatus,
    AdjointOptimization, AdjointIteration, AdjointOptStatus,
    AeroDatabase, AeroDatabasePoint, AeroDatabaseStatus,
)


class OpenFOAMAdvancedService:

    def run_parametric_study(
        self,
        model_id: str,
        project_id: str,
        tenant_id: str,
        sweep_ranges: list[dict[str, Any]],
        solver: str = "simpleFoam",
        turbulence_model: str = "kOmegaSST",
        max_parallel: int = 4,
    ) -> ParametricStudy:
        ranges = [
            SweepRange(
                parameter=sr["parameter"],
                start=sr["start"],
                end=sr["end"],
                step=sr["step"],
                unit=sr.get("unit", ""),
            )
            for sr in sweep_ranges
        ]
        study = ParametricStudy(
            model_id=model_id,
            project_id=project_id,
            tenant_id=tenant_id,
            sweep_ranges=ranges,
            solver=solver,
            turbulence_model=turbulence_model,
            max_parallel_cases=max_parallel,
        )
        study.calculate_total_cases()

        study.status = ParametricStudyStatus.GENERATING_CASES
        param_combos = self._generate_parameter_combinations(ranges)

        study.status = ParametricStudyStatus.RUNNING
        for i, params in enumerate(param_combos):
            result = self._simulate_single_case(i, params, solver, turbulence_model)
            study.add_case_result(result)

        study.status = ParametricStudyStatus.POST_PROCESSING
        study.complete_study()
        return study

    def _generate_parameter_combinations(
        self, ranges: list[SweepRange]
    ) -> list[dict[str, float]]:
        if not ranges:
            return [{}]

        all_points = [sr.to_points() for sr in ranges]
        param_names = [sr.parameter for sr in ranges]

        combos: list[dict[str, float]] = [{}]
        for idx, points in enumerate(all_points):
            new_combos = []
            for combo in combos:
                for pt in points:
                    new_combo = {**combo, param_names[idx]: pt}
                    new_combos.append(new_combo)
            combos = new_combos

        return combos

    def _simulate_single_case(
        self,
        case_index: int,
        parameters: dict[str, float],
        solver: str,
        turbulence_model: str,
    ) -> CaseResult:
        alpha = parameters.get("angle_of_attack", 0.0)
        mach = parameters.get("mach_number", 0.3)
        re = parameters.get("reynolds_number", 1e6)

        cl = 2 * math.pi * math.radians(alpha) * (1 - 0.05 * mach ** 2)
        cd = 0.01 + 0.05 * alpha ** 2 + 0.1 * mach ** 2
        cm = -0.1 * cl

        convergence = "converged" if abs(alpha) < 15 and mach < 0.8 else "not_converged"

        return CaseResult(
            case_id=f"case-{case_index:04d}",
            parameters=parameters,
            lift_coefficient=round(cl, 6),
            drag_coefficient=round(cd, 6),
            moment_coefficient=round(cm, 6),
            convergence_status=convergence,
        )

    def run_adjoint_optimization(
        self,
        model_id: str,
        project_id: str,
        tenant_id: str,
        objective_function: str = "minimize_drag",
        max_iterations: int = 20,
        convergence_tolerance: float = 1e-4,
        step_size: float = 0.01,
    ) -> AdjointOptimization:
        opt = AdjointOptimization(
            model_id=model_id,
            project_id=project_id,
            tenant_id=tenant_id,
            objective_function=objective_function,
            max_iterations=max_iterations,
            convergence_tolerance=convergence_tolerance,
            step_size=step_size,
        )

        opt.status = AdjointOptStatus.RUNNING
        objective = 0.05

        for i in range(1, max_iterations + 1):
            gradient_norm = 0.01 / (1 + 0.1 * i)
            geometry_update = step_size * gradient_norm
            objective *= (1 - 0.05 * step_size * 10)

            converged = gradient_norm < convergence_tolerance

            iteration = AdjointIteration(
                iteration=i,
                objective_value=round(objective, 8),
                sensitivity_norm=round(gradient_norm, 8),
                geometry_update_norm=round(geometry_update, 8),
                converged=converged,
            )
            opt.add_iteration(iteration)

            if converged:
                break

        opt.complete()
        return opt

    def generate_aero_database(
        self,
        model_id: str,
        project_id: str,
        tenant_id: str,
        alpha_range: dict[str, Any] | None = None,
        mach_range: dict[str, Any] | None = None,
        beta_range: dict[str, Any] | None = None,
    ) -> AeroDatabase:
        a_alpha = SweepRange(**alpha_range) if alpha_range else SweepRange("angle_of_attack", -5, 15, 1, "deg")
        a_mach = SweepRange(**mach_range) if mach_range else SweepRange("mach_number", 0.1, 0.8, 0.1)
        a_beta = SweepRange(**beta_range) if beta_range else SweepRange("sideslip_angle", -5, 5, 5, "deg")

        db = AeroDatabase(
            model_id=model_id,
            project_id=project_id,
            tenant_id=tenant_id,
            alpha_range=a_alpha,
            mach_range=a_mach,
            beta_range=a_beta,
        )
        db.calculate_total_points()

        db.status = AeroDatabaseStatus.RUNNING

        for alpha in a_alpha.to_points():
            for mach in a_mach.to_points():
                for beta in a_beta.to_points():
                    cl = 2 * math.pi * math.radians(alpha) * (1 - 0.05 * mach ** 2) + 0.01 * beta
                    cd = 0.01 + 0.05 * alpha ** 2 + 0.1 * mach ** 2 + 0.02 * abs(beta)
                    cm = -0.1 * cl + 0.005 * beta

                    convergence = "converged" if abs(alpha) < 15 and mach < 0.85 else "not_converged"

                    point = AeroDatabasePoint(
                        angle_of_attack=alpha,
                        mach_number=mach,
                        sideslip_angle=beta,
                        cl=round(cl, 6),
                        cd=round(cd, 6),
                        cm=round(cm, 6),
                        convergence=convergence,
                    )
                    db.add_data_point(point)

        db.complete()
        return db

    def get_parametric_study(self, study_id: str, studies: dict[str, ParametricStudy]) -> ParametricStudy | None:
        return studies.get(study_id)

    def get_adjoint_optimization(self, opt_id: str, opts: dict[str, AdjointOptimization]) -> AdjointOptimization | None:
        return opts.get(opt_id)

    def get_aero_database(self, db_id: str, dbs: dict[str, AeroDatabase]) -> AeroDatabase | None:
        return dbs.get(db_id)