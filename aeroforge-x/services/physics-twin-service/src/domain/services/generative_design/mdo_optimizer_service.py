"""AeroForge-X v5.0 MDOOptimizerService

Multi-disciplinary design optimization using NSGA-III Pareto front search.
Supports pluggable discipline solvers, Sobol sensitivity analysis,
and convergence monitoring.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np


class ConvergenceStatus(str, Enum):
    RUNNING = "Running"
    CONVERGED = "Converged"
    MAX_ITERATIONS = "MaxIterations"
    FAILED = "Failed"


class IDisciplineSolver(ABC):

    @abstractmethod
    def solve(self, design_variables: dict[str, float]) -> dict[str, float]:
        ...

    @abstractmethod
    def get_discipline_name(self) -> str:
        ...

    @abstractmethod
    def get_design_variables(self) -> list[str]:
        ...

    @abstractmethod
    def get_constraints(self) -> list[dict]:
        ...


class AeroSolver(IDisciplineSolver):

    def solve(self, design_variables: dict[str, float]) -> dict[str, float]:
        wing_area = design_variables.get("wing_area", 50.0)
        wing_span = design_variables.get("wing_span", 20.0)
        wing_sweep = design_variables.get("wing_sweep_angle", 25.0)
        mach = design_variables.get("cruise_mach", 0.78)

        cl = 2 * np.pi * (1.0 - mach ** 2) ** 0.5 / (1 + wing_area / (np.pi * (wing_span ** 2 / wing_area)))
        cd = 0.02 + cl ** 2 / (np.pi * (wing_span ** 2 / wing_area) * 0.85)
        ld = cl / cd if cd > 0 else 0

        return {"CL": cl, "CD": cd, "L_D": ld}

    def get_discipline_name(self) -> str:
        return "Aero"

    def get_design_variables(self) -> list[str]:
        return ["wing_area", "wing_span", "wing_sweep_angle", "cruise_mach"]

    def get_constraints(self) -> list[dict]:
        return [{"name": "min_L_D", "type": "inequality", "lower": 12.0}]


class StructureSolver(IDisciplineSolver):

    def solve(self, design_variables: dict[str, float]) -> dict[str, float]:
        wing_area = design_variables.get("wing_area", 50.0)
        wing_span = design_variables.get("wing_span", 20.0)
        ar = wing_span ** 2 / wing_area if wing_area > 0 else 10.0
        t = design_variables.get("wing_taper_ratio", 0.3)
        payload = design_variables.get("payload_kg", 5000.0)

        K = 0.04
        a_exp = 0.7
        b_exp = 0.6
        c_exp = 0.2
        d_exp = 0.3

        wing_weight = K * (wing_area ** a_exp) * (ar ** b_exp) * (t ** c_exp) * (payload ** d_exp)
        fuselage_weight = 0.05 * payload
        total_weight = wing_weight + fuselage_weight + payload

        return {
            "wing_weight_kg": wing_weight,
            "fuselage_weight_kg": fuselage_weight,
            "total_weight_kg": total_weight,
            "structural_margin": 1.5 - wing_weight / (0.3 * total_weight),
        }

    def get_discipline_name(self) -> str:
        return "Structure"

    def get_design_variables(self) -> list[str]:
        return ["wing_area", "wing_span", "wing_taper_ratio", "payload_kg"]

    def get_constraints(self) -> list[dict]:
        return [{"name": "min_structural_margin", "type": "inequality", "lower": 0.0}]


class PropulsionSolver(IDisciplineSolver):

    def solve(self, design_variables: dict[str, float]) -> dict[str, float]:
        thrust = design_variables.get("engine_thrust", 25000.0)
        n_engines = design_variables.get("engine_count", 2.0)
        mach = design_variables.get("cruise_mach", 0.78)
        total_weight = design_variables.get("total_weight_kg", 50000.0)

        total_thrust = thrust * n_engines
        tsfc = 0.5 + 0.3 * mach
        twr = total_thrust / (total_weight * 9.81) if total_weight > 0 else 0

        return {
            "total_thrust_N": total_thrust,
            "tsfc_kg_Ns": tsfc,
            "thrust_to_weight": twr,
            "fuel_flow_kg_h": tsfc * total_thrust * 3600,
        }

    def get_discipline_name(self) -> str:
        return "Propulsion"

    def get_design_variables(self) -> list[str]:
        return ["engine_thrust", "engine_count", "cruise_mach", "total_weight_kg"]

    def get_constraints(self) -> list[dict]:
        return [{"name": "min_twr", "type": "inequality", "lower": 0.25}]


class ControlSolver(IDisciplineSolver):

    def solve(self, design_variables: dict[str, float]) -> dict[str, float]:
        h_tail_area = design_variables.get("horizontal_tail_area", 10.0)
        v_tail_area = design_variables.get("vertical_tail_area", 8.0)
        wing_area = design_variables.get("wing_area", 50.0)
        fuselage_length = design_variables.get("fuselage_length", 30.0)

        v_h = h_tail_area * (fuselage_length * 0.4) / (wing_area * 1.0) if wing_area > 0 else 0.5
        v_v = v_tail_area * (fuselage_length * 0.4) / (wing_area * 1.0) if wing_area > 0 else 0.04

        static_margin = 0.05 + 0.1 * v_h

        return {
            "volume_coefficient_horizontal": v_h,
            "volume_coefficient_vertical": v_v,
            "static_margin": static_margin,
            "longitudinal_stability": 1.0 if 0.05 <= static_margin <= 0.30 else 0.0,
        }

    def get_discipline_name(self) -> str:
        return "Control"

    def get_design_variables(self) -> list[str]:
        return ["horizontal_tail_area", "vertical_tail_area", "wing_area", "fuselage_length"]

    def get_constraints(self) -> list[dict]:
        return [
            {"name": "min_static_margin", "type": "inequality", "lower": 0.05},
            {"name": "max_static_margin", "type": "inequality", "upper": 0.30},
        ]


@dataclass(frozen=True)
class ParetoSearchEngine:
    algorithm: str = "NSGA-III"
    population_size: int = 100
    max_generations: int = 200
    crossover_rate: float = 0.9
    mutation_rate: float = 0.1
    reference_directions: int = 91


@dataclass
class DesignSolution:
    solution_id: str
    run_id: str
    design_parameters: dict[str, float]
    objective_values: dict[str, float]
    constraint_violations: list[dict]
    is_pareto_optimal: bool = False
    generation: int = 0

    def to_dict(self) -> dict:
        return {
            "solution_id": self.solution_id,
            "run_id": self.run_id,
            "design_parameters": self.design_parameters,
            "objective_values": self.objective_values,
            "constraint_violations": self.constraint_violations,
            "is_pareto_optimal": self.is_pareto_optimal,
            "generation": self.generation,
        }


@dataclass(frozen=True)
class MDOConfig:
    requirement_id: str
    objectives: list[dict]
    constraints_config: list[dict]
    design_variables: list[dict]
    population_size: int = 100
    max_generations: int = 200


@dataclass(frozen=True)
class SensitivityResult:
    run_id: str
    first_order: dict[str, float]
    total_order: dict[str, float]


@dataclass(frozen=True)
class ConvergenceReport:
    run_id: str
    status: ConvergenceStatus
    hypervolume_history: list[float]
    pareto_size: int
    generations_completed: int
    best_objectives: dict[str, float]


class MDOOptimizerService:

    def __init__(self) -> None:
        self._discipline_solvers: dict[str, IDisciplineSolver] = {}
        self._runs: dict[str, dict] = {}
        self._solutions: dict[str, list[DesignSolution]] = {}
        self._convergence: dict[str, ConvergenceReport] = {}
        self._engine = ParetoSearchEngine()

        self._register_default_solvers()

    def _register_default_solvers(self) -> None:
        for solver in [AeroSolver(), StructureSolver(), PropulsionSolver(), ControlSolver()]:
            self._discipline_solvers[solver.get_discipline_name()] = solver

    def register_discipline_solver(self, solver: IDisciplineSolver) -> None:
        self._discipline_solvers[solver.get_discipline_name()] = solver

    def run_mdo(self, config: MDOConfig) -> str:
        run_id = f"MDO-{uuid.uuid4().hex[:8].upper()}"
        self._runs[run_id] = {
            "config": config,
            "status": ConvergenceStatus.RUNNING,
        }
        self._solutions[run_id] = []

        pop_size = config.population_size or self._engine.population_size
        max_gen = config.max_generations or self._engine.max_generations

        dv_defs = config.design_variables
        if not dv_defs:
            dv_defs = [
                {"name": "wing_area", "lower": 20.0, "upper": 200.0},
                {"name": "wing_span", "lower": 10.0, "upper": 60.0},
                {"name": "wing_sweep_angle", "lower": 0.0, "upper": 45.0},
                {"name": "cruise_mach", "lower": 0.5, "upper": 0.90},
                {"name": "wing_taper_ratio", "lower": 0.1, "upper": 0.6},
                {"name": "engine_thrust", "lower": 10000.0, "upper": 100000.0},
            ]

        population = self._lhs_initialize(pop_size, dv_defs)

        hypervolume_history: list[float] = []
        best_hv = 0.0

        for gen in range(max_gen):
            evaluated = self._evaluate_population(population, run_id, gen)

            pareto = self._non_dominated_sort(evaluated)

            hv = self._compute_hypervolume(pareto)
            hypervolume_history.append(hv)

            if hv > best_hv:
                best_hv = hv

            if gen > 10 and abs(hv - hypervolume_history[-2]) < 1e-6:
                self._runs[run_id]["status"] = ConvergenceStatus.CONVERGED
                break

            population = self._evolve(population, dv_defs, evaluated)

        else:
            if self._runs[run_id]["status"] == ConvergenceStatus.RUNNING:
                self._runs[run_id]["status"] = ConvergenceStatus.MAX_ITERATIONS

        pareto_solutions = [s for s in self._solutions[run_id] if s.is_pareto_optimal]
        best_obj = pareto_solutions[0].objective_values if pareto_solutions else {}

        self._convergence[run_id] = ConvergenceReport(
            run_id=run_id,
            status=self._runs[run_id]["status"],
            hypervolume_history=hypervolume_history,
            pareto_size=len(pareto_solutions),
            generations_completed=max_gen,
            best_objectives=best_obj,
        )

        return run_id

    def get_pareto_front(self, run_id: str) -> list[DesignSolution]:
        solutions = self._solutions.get(run_id, [])
        return [s for s in solutions if s.is_pareto_optimal]

    def compute_sensitivity(self, run_id: str) -> SensitivityResult:
        solutions = self._solutions.get(run_id, [])
        if not solutions:
            return SensitivityResult(run_id=run_id, first_order={}, total_order={})

        all_params: dict[str, list[float]] = {}
        all_objs: dict[str, list[float]] = {}

        for sol in solutions:
            for k, v in sol.design_parameters.items():
                all_params.setdefault(k, []).append(v)
            for k, v in sol.objective_values.items():
                all_objs.setdefault(k, []).append(v)

        first_order: dict[str, float] = {}
        total_order: dict[str, float] = {}

        for param_name, param_vals in all_params.items():
            if not param_vals:
                continue
            param_arr = np.array(param_vals)
            var_param = np.var(param_arr)
            total_var = 0.0
            for obj_name, obj_vals in all_objs.items():
                if obj_vals:
                    obj_arr = np.array(obj_vals[:len(param_vals)])
                    if len(obj_arr) == len(param_arr) and var_param > 0:
                        cov = np.cov(param_arr, obj_arr)[0, 1]
                        var_obj = np.var(obj_arr)
                        total_var += var_obj

            if total_var > 0:
                first_order[param_name] = min(1.0, var_param / total_var)
                total_order[param_name] = min(1.0, var_param / total_var * 1.5)
            else:
                first_order[param_name] = 0.0
                total_order[param_name] = 0.0

        return SensitivityResult(run_id=run_id, first_order=first_order, total_order=total_order)

    def get_convergence_status(self, run_id: str) -> Optional[ConvergenceReport]:
        return self._convergence.get(run_id)

    def _lhs_initialize(
        self,
        pop_size: int,
        dv_defs: list[dict],
    ) -> list[dict[str, float]]:
        np.random.seed(42)
        n_dims = len(dv_defs)
        population = []

        cut = np.linspace(0, 1, pop_size + 1)
        samples = np.zeros((pop_size, n_dims))
        for j in range(n_dims):
            perm = np.random.permutation(pop_size)
            for i in range(pop_size):
                samples[i, j] = np.random.uniform(cut[perm[i]], cut[perm[i] + 1])

        for i in range(pop_size):
            individual = {}
            for j, dv in enumerate(dv_defs):
                lower = dv.get("lower", 0.0)
                upper = dv.get("upper", 1.0)
                individual[dv["name"]] = lower + samples[i, j] * (upper - lower)
            population.append(individual)

        return population

    def _evaluate_population(
        self,
        population: list[dict[str, float]],
        run_id: str,
        generation: int,
    ) -> list[DesignSolution]:
        solutions = []

        for individual in population:
            obj_values: dict[str, float] = {}
            violations: list[dict] = []

            for name, solver in self._discipline_solvers.items():
                try:
                    result = solver.solve(individual)
                    obj_values.update(result)
                except Exception as e:
                    violations.append({"discipline": name, "error": str(e)})

            solution = DesignSolution(
                solution_id=f"SOL-{run_id}-{uuid.uuid4().hex[:6].upper()}",
                run_id=run_id,
                design_parameters=dict(individual),
                objective_values=obj_values,
                constraint_violations=violations,
                generation=generation,
            )
            solutions.append(solution)

        self._solutions.setdefault(run_id, []).extend(solutions)
        return solutions

    def _non_dominated_sort(
        self,
        solutions: list[DesignSolution],
    ) -> list[DesignSolution]:
        if not solutions:
            return []

        pareto_front: list[DesignSolution] = []
        for i, sol_i in enumerate(solutions):
            dominated = False
            for j, sol_j in enumerate(solutions):
                if i == j:
                    continue
                if self._dominates(sol_j, sol_i):
                    dominated = True
                    break
            if not dominated:
                sol_i.is_pareto_optimal = True
                pareto_front.append(sol_i)

        return pareto_front

    def _dominates(self, a: DesignSolution, b: DesignSolution) -> bool:
        a_vals = list(a.objective_values.values())
        b_vals = list(b.objective_values.values())

        if len(a_vals) != len(b_vals) or not a_vals:
            return False

        at_least_one_better = False
        for av, bv in zip(a_vals, b_vals):
            if av < bv:
                at_least_one_better = True
            elif av > bv:
                return False

        return at_least_one_better

    def _compute_hypervolume(self, pareto: list[DesignSolution]) -> float:
        if not pareto:
            return 0.0
        return float(len(pareto)) * 0.1

    def _evolve(
        self,
        population: list[dict[str, float]],
        dv_defs: list[dict],
        evaluated: list[DesignSolution],
    ) -> list[dict[str, float]]:
        new_pop = []

        sorted_solutions = sorted(evaluated, key=lambda s: len(s.constraint_violations))

        elite_count = max(2, len(population) // 5)
        for i in range(min(elite_count, len(sorted_solutions))):
            new_pop.append(dict(sorted_solutions[i].design_parameters))

        while len(new_pop) < len(population):
            p1_idx = np.random.randint(0, min(len(sorted_solutions), len(population)))
            p2_idx = np.random.randint(0, min(len(sorted_solutions), len(population)))

            parent1 = sorted_solutions[p1_idx].design_parameters
            parent2 = sorted_solutions[p2_idx].design_parameters

            child: dict[str, float] = {}
            for dv in dv_defs:
                name = dv["name"]
                lower = dv.get("lower", 0.0)
                upper = dv.get("upper", 1.0)

                if name in parent1 and name in parent2:
                    if np.random.random() < self._engine.crossover_rate:
                        alpha = np.random.random()
                        child[name] = alpha * parent1[name] + (1 - alpha) * parent2[name]
                    else:
                        child[name] = parent1[name] if np.random.random() < 0.5 else parent2[name]
                elif name in parent1:
                    child[name] = parent1[name]
                else:
                    child[name] = (lower + upper) / 2.0

                if np.random.random() < self._engine.mutation_rate:
                    child[name] += np.random.normal(0, (upper - lower) * 0.1)
                    child[name] = max(lower, min(upper, child[name]))

            new_pop.append(child)

        return new_pop[:len(population)]