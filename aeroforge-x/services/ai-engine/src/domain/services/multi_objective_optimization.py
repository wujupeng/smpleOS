from __future__ import annotations

import logging
import math
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class OptimizationObjective:
    def __init__(self, name: str, direction: str = "minimize", weight: float = 1.0, target: float | None = None):
        self.name = name
        self.direction = direction
        self.weight = weight
        self.target = target

    def evaluate(self, value: float) -> float:
        if self.direction == "minimize":
            return value * self.weight
        else:
            return -value * self.weight


class OptimizationConstraint:
    def __init__(self, name: str, constraint_type: str, bound: float, variable: str | None = None):
        self.name = name
        self.constraint_type = constraint_type
        self.bound = bound
        self.variable = variable

    def is_satisfied(self, value: float) -> bool:
        if self.constraint_type == "less_than":
            return value <= self.bound
        elif self.constraint_type == "greater_than":
            return value >= self.bound
        elif self.constraint_type == "equal":
            return abs(value - self.bound) < 1e-6
        return True


class ParetoPoint:
    def __init__(self, point_id: str, design_variables: dict[str, float], objectives: dict[str, float], is_feasible: bool = True):
        self.point_id = point_id
        self.design_variables = design_variables
        self.objectives = objectives
        self.is_feasible = is_feasible

    def to_dict(self) -> dict[str, Any]:
        return {
            "point_id": self.point_id,
            "design_variables": self.design_variables,
            "objectives": self.objectives,
            "is_feasible": self.is_feasible,
        }


class OptimizationResult:
    def __init__(self, result_id: str, task_id: str):
        self.result_id = result_id
        self.task_id = task_id
        self.pareto_front: list[ParetoPoint] = []
        self.infeasible_regions: list[dict[str, Any]] = []
        self.best_compromise: ParetoPoint | None = None
        self.iteration_count: int = 0
        self.convergence_achieved: bool = False
        self.baseline_frozen_violation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "task_id": self.task_id,
            "pareto_front": [p.to_dict() for p in self.pareto_front],
            "infeasible_regions": self.infeasible_regions,
            "best_compromise": self.best_compromise.to_dict() if self.best_compromise else None,
            "iteration_count": self.iteration_count,
            "convergence_achieved": self.convergence_achieved,
            "baseline_frozen_violation": self.baseline_frozen_violation,
        }


class MultiObjectiveOptimization:
    def __init__(self, event_publisher: Any | None = None):
        self._event_publisher = event_publisher
        self._frozen_baselines: set[str] = set()
        self._results: dict[str, OptimizationResult] = {}

    def freeze_baseline(self, task_id: str) -> None:
        self._frozen_baselines.add(task_id)

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def optimize(self, task_id: str, objectives: list[dict[str, Any]], constraints: list[dict[str, Any]], design_variables: dict[str, dict[str, float]], max_iterations: int = 100) -> OptimizationResult:
        result = OptimizationResult(result_id=str(uuid4()), task_id=task_id)

        if task_id in self._frozen_baselines:
            result.baseline_frozen_violation = True
            self._results[result.result_id] = result
            return result

        obj_list = [
            OptimizationObjective(
                name=o["name"],
                direction=o.get("direction", "minimize"),
                weight=o.get("weight", 1.0),
            )
            for o in objectives
        ]

        constraint_list = [
            OptimizationConstraint(
                name=c["name"],
                constraint_type=c.get("type", "less_than"),
                bound=c["bound"],
                variable=c.get("variable"),
            )
            for c in constraints
        ]

        population_size = 50
        population = self._initialize_population(design_variables, population_size)

        for iteration in range(max_iterations):
            evaluated = []
            for individual in population:
                obj_values = self._evaluate_objectives(individual, obj_list, design_variables)
                feasible = self._check_constraints(individual, constraint_list, design_variables)
                point = ParetoPoint(
                    point_id=f"P-{iteration}-{len(evaluated)}",
                    design_variables=individual,
                    objectives=obj_values,
                    is_feasible=feasible,
                )
                evaluated.append(point)

            non_dominated = self._find_non_dominated(evaluated)
            result.pareto_front.extend(non_dominated)

            population = self._evolve_population(population, evaluated, design_variables)

        result.pareto_front = self._find_non_dominated(result.pareto_front)
        result.iteration_count = max_iterations
        result.convergence_achieved = len(result.pareto_front) > 0

        infeasible = [p for p in result.pareto_front if not p.is_feasible]
        if infeasible:
            result.infeasible_regions = [
                {"design_variables": p.design_variables, "constraint_violations": [k for k, v in p.objectives.items() if v < 0]}
                for p in infeasible
            ]
            result.pareto_front = [p for p in result.pareto_front if p.is_feasible] + infeasible[:5]

        if result.pareto_front:
            result.best_compromise = self._find_best_compromise(result.pareto_front, obj_list)

        self._results[result.result_id] = result
        return result

    def _initialize_population(self, design_variables: dict[str, dict[str, float]], size: int) -> list[dict[str, float]]:
        import random
        population = []
        for _ in range(size):
            individual = {}
            for var_name, var_range in design_variables.items():
                min_val = var_range.get("min", 0.0)
                max_val = var_range.get("max", 100.0)
                individual[var_name] = min_val + random.random() * (max_val - min_val)
            population.append(individual)
        return population

    def _evaluate_objectives(self, individual: dict[str, float], objectives: list[OptimizationObjective], design_variables: dict[str, dict[str, float]]) -> dict[str, float]:
        results = {}
        for obj in objectives:
            if obj.name == "weight":
                wingspan = individual.get("wingspan_m", 35.8)
                length = individual.get("fuselage_length_m", 40.0)
                results["weight"] = wingspan * length * 12.0
            elif obj.name == "cost":
                mtow = individual.get("mtow_kg", 80000)
                results["cost"] = mtow * 1500.0
            elif obj.name == "lift_drag_ratio":
                ar = individual.get("aspect_ratio", 9.0)
                sweep = individual.get("sweep_angle_deg", 25.0)
                cd0 = 0.02
                k = 1.0 / (math.pi * ar * 0.85 * math.cos(math.radians(sweep)))
                optimal_ld = 0.5 * math.sqrt(1.0 / (cd0 * k))
                results["lift_drag_ratio"] = optimal_ld
            else:
                val = sum(individual.values()) / max(len(individual), 1)
                results[obj.name] = val
        return results

    def _check_constraints(self, individual: dict[str, float], constraints: list[OptimizationConstraint], design_variables: dict[str, dict[str, float]]) -> bool:
        for constraint in constraints:
            if constraint.variable and constraint.variable in individual:
                if not constraint.is_satisfied(individual[constraint.variable]):
                    return False
        return True

    def _find_non_dominated(self, points: list[ParetoPoint]) -> list[ParetoPoint]:
        feasible = [p for p in points if p.is_feasible]
        if not feasible:
            return points[:10]

        non_dominated = []
        for i, p in enumerate(feasible):
            dominated = False
            for j, q in enumerate(feasible):
                if i == j:
                    continue
                if self._dominates(q, p):
                    dominated = True
                    break
            if not dominated:
                non_dominated.append(p)
        return non_dominated if non_dominated else feasible[:10]

    def _dominates(self, a: ParetoPoint, b: ParetoPoint) -> bool:
        at_least_one_better = False
        for key in a.objectives:
            if key not in b.objectives:
                continue
            if a.objectives[key] < b.objectives[key]:
                at_least_one_better = True
            elif a.objectives[key] > b.objectives[key]:
                return False
        return at_least_one_better

    def _evolve_population(self, population: list[dict[str, float]], evaluated: list[ParetoPoint], design_variables: dict[str, dict[str, float]]) -> list[dict[str, float]]:
        import random
        feasible = [p for p in evaluated if p.is_feasible]
        if not feasible:
            return self._initialize_population(design_variables, len(population))

        new_population = []
        sorted_points = sorted(feasible, key=lambda p: sum(p.objectives.values()))
        elite = [p.design_variables for p in sorted_points[:max(len(sorted_points) // 4, 2)]]
        new_population.extend(elite)

        while len(new_population) < len(population):
            parent1 = random.choice(elite)
            parent2 = random.choice(elite)
            child = {}
            for var in design_variables:
                if random.random() < 0.5:
                    child[var] = parent1.get(var, design_variables[var].get("min", 0))
                else:
                    child[var] = parent2.get(var, design_variables[var].get("min", 0))
                min_val = design_variables[var].get("min", 0.0)
                max_val = design_variables[var].get("max", 100.0)
                child[var] += random.gauss(0, (max_val - min_val) * 0.05)
                child[var] = max(min_val, min(max_val, child[var]))
            new_population.append(child)

        return new_population

    def _find_best_compromise(self, pareto_front: list[ParetoPoint], objectives: list[OptimizationObjective]) -> ParetoPoint:
        if not pareto_front:
            return pareto_front[0]

        feasible = [p for p in pareto_front if p.is_feasible]
        if not feasible:
            feasible = pareto_front

        obj_values = {obj.name: [p.objectives.get(obj.name, 0) for p in feasible] for obj in objectives}
        normalized = []
        for p in feasible:
            score = 0.0
            for obj in objectives:
                vals = obj_values[obj.name]
                min_v, max_v = min(vals), max(vals)
                range_v = max_v - min_v if max_v != min_v else 1.0
                norm = (p.objectives.get(obj.name, 0) - min_v) / range_v
                if obj.direction == "maximize":
                    norm = 1.0 - norm
                score += norm * obj.weight
            normalized.append((score, p))

        normalized.sort(key=lambda x: x[0])
        return normalized[0][1]

    def get_result(self, result_id: str) -> OptimizationResult | None:
        return self._results.get(result_id)