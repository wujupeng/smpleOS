from __future__ import annotations

import logging
import random
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .entities.optimization_task import (
    OptimizationTask, OptimizationType, OptimizationStatus, OptimizationAlgorithm,
    ObjectiveFunction, OptimizationConstraint, DesignVariable, ParetoSolution,
)

logger = logging.getLogger(__name__)

BUILTIN_OBJECTIVES: dict[str, ObjectiveFunction] = {
    "minimize_weight": ObjectiveFunction(name="minimize_weight", direction="minimize", weight=1.0),
    "maximize_lift_drag_ratio": ObjectiveFunction(name="maximize_lift_drag_ratio", direction="maximize", weight=1.0),
    "minimize_cost": ObjectiveFunction(name="minimize_cost", direction="minimize", weight=0.5),
    "maximize_range": ObjectiveFunction(name="maximize_range", direction="maximize", weight=0.8),
    "maximize_payload": ObjectiveFunction(name="maximize_payload", direction="maximize", weight=0.7),
}

BUILTIN_CONSTRAINTS: dict[str, OptimizationConstraint] = {
    "safety_factor": OptimizationConstraint(name="safety_factor", operator=">=", value=1.5, description="安全系数≥1.5"),
    "min_lift_drag": OptimizationConstraint(name="lift_drag_ratio", operator=">=", value=8.0, description="升阻比≥8"),
    "max_deformation": OptimizationConstraint(name="max_deformation_mm", operator="<=", value=5.0, description="最大变形≤5mm"),
    "max_stress": OptimizationConstraint(name="max_stress_mpa", operator="<=", value=350.0, description="最大应力≤350MPa"),
}

BUILTIN_DESIGN_VARIABLES: dict[str, DesignVariable] = {
    "wing_span": DesignVariable(name="wing_span", lower_bound=5.0, upper_bound=30.0, initial_value=15.0),
    "aspect_ratio": DesignVariable(name="aspect_ratio", lower_bound=4.0, upper_bound=20.0, initial_value=8.0),
    "wing_sweep_deg": DesignVariable(name="wing_sweep_deg", lower_bound=0.0, upper_bound=45.0, initial_value=5.0),
    "thickness_ratio": DesignVariable(name="thickness_ratio", lower_bound=0.06, upper_bound=0.20, initial_value=0.12),
    "taper_ratio": DesignVariable(name="taper_ratio", lower_bound=0.2, upper_bound=1.0, initial_value=0.6),
    "fuselage_length": DesignVariable(name="fuselage_length", lower_bound=5.0, upper_bound=30.0, initial_value=12.0),
}


class MultiObjectiveOptimizer:
    def __init__(self) -> None:
        self._tasks: dict[str, OptimizationTask] = {}

    def create_optimization_task(
        self,
        project_id: str,
        tenant_id: str,
        objective_names: list[str],
        constraint_names: list[str],
        variable_names: list[str],
        algorithm: OptimizationAlgorithm = OptimizationAlgorithm.NSGA2,
        max_iterations: int = 100,
        population_size: int = 50,
    ) -> OptimizationTask:
        objectives = [BUILTIN_OBJECTIVES[n] for n in objective_names if n in BUILTIN_OBJECTIVES]
        if not objectives:
            objectives = [BUILTIN_OBJECTIVES["minimize_weight"], BUILTIN_OBJECTIVES["maximize_lift_drag_ratio"]]

        constraints = [BUILTIN_CONSTRAINTS[n] for n in constraint_names if n in BUILTIN_CONSTRAINTS]
        if not constraints:
            constraints = [BUILTIN_CONSTRAINTS["safety_factor"]]

        design_variables = [BUILTIN_DESIGN_VARIABLES[n] for n in variable_names if n in BUILTIN_DESIGN_VARIABLES]
        if not design_variables:
            design_variables = [BUILTIN_DESIGN_VARIABLES["wing_span"], BUILTIN_DESIGN_VARIABLES["aspect_ratio"]]

        task = OptimizationTask(
            project_id=project_id,
            tenant_id=tenant_id,
            optimization_type=OptimizationType.MULTI_OBJECTIVE,
            objectives=objectives,
            constraints=constraints,
            design_variables=design_variables,
            algorithm=algorithm,
            max_iterations=max_iterations,
            population_size=population_size,
        )

        self._tasks[task.id] = task

        task.add_domain_event(DomainEvent(
            event_type="optimization.queued",
            aggregate_id=task.id,
            payload={"task_id": task.id, "objectives": [o.name for o in objectives]},
        ))

        logger.info("Created optimization task %s with %d objectives", task.id, len(objectives))
        return task

    def run_optimization(self, task_id: str) -> OptimizationTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None

        task.start()

        try:
            pareto_front = self._run_nsga2(task)
            optimal = self._recommend_optimal(pareto_front, task.objectives)
            task.complete(pareto_front, optimal)
            logger.info("Optimization task %s completed with %d pareto solutions", task_id, len(pareto_front))
        except Exception as e:
            task.fail(str(e))
            logger.error("Optimization task %s failed: %s", task_id, e)

        return task

    def get_task(self, task_id: str) -> OptimizationTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self, project_id: str | None = None) -> list[OptimizationTask]:
        tasks = list(self._tasks.values())
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        return tasks

    def _run_nsga2(self, task: OptimizationTask) -> list[ParetoSolution]:
        population: list[dict[str, float]] = []
        for _ in range(task.population_size):
            individual = {}
            for var in task.design_variables:
                individual[var.name] = random.uniform(var.lower_bound, var.upper_bound)
            population.append(individual)

        for iteration in range(task.max_iterations):
            evaluated = []
            for individual in population:
                obj_values = self._evaluate_objectives(individual, task.objectives)
                con_values = self._evaluate_constraints(individual, task.constraints)
                is_feasible = all(c.is_satisfied(con_values.get(c.name, 0.0)) for c in task.constraints)
                evaluated.append((individual, obj_values, con_values, is_feasible))

            task.iteration_count = iteration + 1
            convergence = {
                "iteration": iteration + 1,
                "feasible_count": sum(1 for e in evaluated if e[3]),
                "best_objectives": {},
            }
            for obj in task.objectives:
                values = [e[1].get(obj.name, 0) for e in evaluated if e[3]]
                if values:
                    if obj.direction == "minimize":
                        convergence["best_objectives"][obj.name] = min(values)
                    else:
                        convergence["best_objectives"][obj.name] = max(values)
            task.convergence_history.append(convergence)

            new_population = []
            for i in range(task.population_size // 2):
                p1 = random.choice(population)
                p2 = random.choice(population)
                child = {}
                for var in task.design_variables:
                    if random.random() < 0.5:
                        child[var.name] = p1.get(var.name, var.initial_value or (var.lower_bound + var.upper_bound) / 2)
                    else:
                        child[var.name] = p2.get(var.name, var.initial_value or (var.lower_bound + var.upper_bound) / 2)
                    if random.random() < 0.1:
                        child[var.name] = random.uniform(var.lower_bound, var.upper_bound)
                    child[var.name] = max(var.lower_bound, min(var.upper_bound, child[var.name]))
                new_population.append(child)
            population.extend(new_population)
            population = population[:task.population_size]

        pareto_front: list[ParetoSolution] = []
        for idx, individual in enumerate(population):
            obj_values = self._evaluate_objectives(individual, task.objectives)
            con_values = self._evaluate_constraints(individual, task.constraints)
            is_feasible = all(c.is_satisfied(con_values.get(c.name, 0.0)) for c in task.constraints)
            pareto_front.append(ParetoSolution(
                solution_id=f"SOL-{idx + 1:04d}",
                variable_values=individual,
                objective_values=obj_values,
                constraint_values=con_values,
                is_feasible=is_feasible,
            ))

        pareto_front = self._non_dominated_sort(pareto_front, task.objectives)
        return pareto_front

    def _evaluate_objectives(self, variables: dict[str, float], objectives: list[ObjectiveFunction]) -> dict[str, float]:
        results: dict[str, float] = {}
        wing_span = variables.get("wing_span", 15.0)
        aspect_ratio = variables.get("aspect_ratio", 8.0)
        thickness_ratio = variables.get("thickness_ratio", 0.12)
        taper_ratio = variables.get("taper_ratio", 0.6)

        wing_area = (wing_span ** 2) / max(aspect_ratio, 1)
        wing_volume = wing_area * wing_span * thickness_ratio * 0.5

        for obj in objectives:
            if obj.name == "minimize_weight":
                results[obj.name] = round(wing_volume * 2700 * 0.3 + wing_span * 5, 2)
            elif obj.name == "maximize_lift_drag_ratio":
                ld = aspect_ratio * 0.8 / (1 + 0.1 / max(aspect_ratio, 1))
                results[obj.name] = round(ld, 2)
            elif obj.name == "minimize_cost":
                results[obj.name] = round(wing_volume * 50 + wing_span * 200, 2)
            elif obj.name == "maximize_range":
                results[obj.name] = round(wing_span * aspect_ratio * 2, 2)
            elif obj.name == "maximize_payload":
                results[obj.name] = round(wing_area * 5, 2)
            else:
                results[obj.name] = round(random.uniform(0, 100), 2)

        return results

    def _evaluate_constraints(self, variables: dict[str, float], constraints: list[OptimizationConstraint]) -> dict[str, float]:
        results: dict[str, float] = {}
        aspect_ratio = variables.get("aspect_ratio", 8.0)
        thickness_ratio = variables.get("thickness_ratio", 0.12)

        for con in constraints:
            if con.name == "safety_factor":
                results[con.name] = round(1.5 + (0.2 - thickness_ratio) * 5, 2)
            elif con.name == "lift_drag_ratio":
                ld = aspect_ratio * 0.8 / (1 + 0.1 / max(aspect_ratio, 1))
                results[con.name] = round(ld, 2)
            elif con.name == "max_deformation_mm":
                results[con.name] = round(2.0 + random.uniform(0, 3), 2)
            elif con.name == "max_stress_mpa":
                results[con.name] = round(200 + random.uniform(0, 150), 2)
            else:
                results[con.name] = round(random.uniform(0, 10), 2)

        return results

    def _non_dominated_sort(self, solutions: list[ParetoSolution], objectives: list[ObjectiveFunction]) -> list[ParetoSolution]:
        feasible = [s for s in solutions if s.is_feasible]
        pareto: list[ParetoSolution] = []

        for i, sol_i in enumerate(feasible):
            dominated = False
            for j, sol_j in enumerate(feasible):
                if i == j:
                    continue
                if self._dominates(sol_j, sol_i, objectives):
                    dominated = True
                    break
            if not dominated:
                sol_i.rank = 0
                pareto.append(sol_i)

        if not pareto and feasible:
            pareto = feasible[:min(10, len(feasible))]

        return pareto

    def _dominates(self, a: ParetoSolution, b: ParetoSolution, objectives: list[ObjectiveFunction]) -> bool:
        at_least_one_better = False
        for obj in objectives:
            a_val = a.objective_values.get(obj.name, 0)
            b_val = b.objective_values.get(obj.name, 0)
            if obj.direction == "minimize":
                if a_val > b_val:
                    return False
                if a_val < b_val:
                    at_least_one_better = True
            else:
                if a_val < b_val:
                    return False
                if a_val > b_val:
                    at_least_one_better = True
        return at_least_one_better

    def _recommend_optimal(self, pareto_front: list[ParetoSolution], objectives: list[ObjectiveFunction]) -> ParetoSolution | None:
        feasible = [s for s in pareto_front if s.is_feasible]
        if not feasible:
            return pareto_front[0] if pareto_front else None

        best = feasible[0]
        best_score = 0.0
        for obj in objectives:
            val = best.objective_values.get(obj.name, 0)
            best_score += obj.weight * (1.0 / max(val, 1e-9) if obj.direction == "minimize" else val)

        for sol in feasible[1:]:
            score = 0.0
            for obj in objectives:
                val = sol.objective_values.get(obj.name, 0)
                score += obj.weight * (1.0 / max(val, 1e-9) if obj.direction == "minimize" else val)
            if score > best_score:
                best_score = score
                best = sol

        return best