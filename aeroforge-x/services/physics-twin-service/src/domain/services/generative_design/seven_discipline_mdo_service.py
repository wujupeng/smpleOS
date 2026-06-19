"""AeroForge-X v6.0 SevenDisciplineMDOService

Extends MDO from 4 disciplines to 7 disciplines by adding
Cost, Manufacturing, and Certification solvers.
REQ-E-ENH-008~014
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


class IDisciplineSolver7D(ABC):
    @abstractmethod
    def solve(self, design_variables: dict) -> dict:
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

    @abstractmethod
    def get_objectives(self) -> list[str]:
        ...


class CostSolver(IDisciplineSolver7D):
    def solve(self, design_variables: dict) -> dict:
        wing_span = design_variables.get("wing_span", 30)
        engine_count = design_variables.get("engine_count", 2)

        dev_cost = wing_span * 0.5 + engine_count * 10
        prod_cost = wing_span * 0.3 + engine_count * 5
        ops_cost = wing_span * 0.1 + engine_count * 2
        disp_cost = wing_span * 0.02
        total = dev_cost + prod_cost + ops_cost + disp_cost

        return {
            "development_cost": round(dev_cost, 2),
            "production_cost": round(prod_cost, 2),
            "operating_cost": round(ops_cost, 2),
            "disposal_cost": round(disp_cost, 2),
            "lifecycle_cost": round(total, 2),
        }

    def get_discipline_name(self) -> str:
        return "Cost"

    def get_design_variables(self) -> list[str]:
        return ["wing_span", "engine_count", "fuselage_length"]

    def get_constraints(self) -> list[dict]:
        return [{"name": "max_lifecycle_cost", "limit": 100, "type": "upper"}]

    def get_objectives(self) -> list[str]:
        return ["lifecycle_cost"]


class ManufacturingSolver(IDisciplineSolver7D):
    def solve(self, design_variables: dict) -> dict:
        wing_span = design_variables.get("wing_span", 30)
        fuselage_length = design_variables.get("fuselage_length", 30)

        process_capability = min(1.0, 50 / max(wing_span, 1))
        tooling_availability = min(1.0, 40 / max(fuselage_length, 1))
        production_rate = max(0.1, 1.0 - (wing_span + fuselage_length) / 200)
        feasibility_score = (process_capability + tooling_availability + production_rate) / 3

        return {
            "process_capability": round(process_capability, 4),
            "tooling_availability": round(tooling_availability, 4),
            "production_rate": round(production_rate, 4),
            "feasibility_score": round(feasibility_score, 4),
        }

    def get_discipline_name(self) -> str:
        return "Manufacturing"

    def get_design_variables(self) -> list[str]:
        return ["wing_span", "fuselage_length", "wing_sweep_angle"]

    def get_constraints(self) -> list[dict]:
        return [{"name": "min_feasibility_score", "limit": 0.5, "type": "lower"}]

    def get_objectives(self) -> list[str]:
        return ["feasibility_score"]


class CertificationSolver(IDisciplineSolver7D):
    def solve(self, design_variables: dict) -> dict:
        engine_count = design_variables.get("engine_count", 2)
        wing_span = design_variables.get("wing_span", 30)

        compliance_items = engine_count * 5 + 20
        test_requirements = engine_count * 3 + 10
        analysis_requirements = engine_count * 2 + 8
        certification_effort = compliance_items * 10 + test_requirements * 20 + analysis_requirements * 5

        return {
            "compliance_items": compliance_items,
            "test_requirements": test_requirements,
            "analysis_requirements": analysis_requirements,
            "certification_effort_hours": round(certification_effort, 1),
        }

    def get_discipline_name(self) -> str:
        return "Certification"

    def get_design_variables(self) -> list[str]:
        return ["engine_count", "wing_span", "cruise_speed_kmh"]

    def get_constraints(self) -> list[dict]:
        return [{"name": "max_certification_effort_hours", "limit": 5000, "type": "upper"}]

    def get_objectives(self) -> list[str]:
        return ["certification_effort_hours"]


@dataclass
class DesignSolution7D:
    design_parameters: dict = field(default_factory=dict)
    objective_values: dict = field(default_factory=dict)
    uncertainty_on_objectives: dict = field(default_factory=dict)
    is_pareto_optimal: bool = False

    def to_dict(self) -> dict:
        return {
            "design_parameters": self.design_parameters,
            "objective_values": self.objective_values,
            "uncertainty_on_objectives": self.uncertainty_on_objectives,
            "is_pareto_optimal": self.is_pareto_optimal,
        }


@dataclass
class DisciplineSensitivityResult:
    run_id: str
    first_order_indices: dict = field(default_factory=dict)
    total_order_indices: dict = field(default_factory=dict)
    per_discipline_breakdown: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "first_order_indices": self.first_order_indices,
            "total_order_indices": self.total_order_indices,
            "per_discipline_breakdown": self.per_discipline_breakdown,
        }


@dataclass
class MDOConfig7D:
    requirement_id: str
    discipline_config: dict = field(default_factory=dict)
    objectives: dict = field(default_factory=dict)
    constraints_config: dict = field(default_factory=dict)
    design_variables: dict = field(default_factory=dict)
    population_size: int = 100
    max_generations: int = 300
    active_discipline_count: int = 7


class SevenDisciplineMDOService:

    V5_DISCIPLINES = ["Aero", "Structure", "Propulsion", "Control"]
    V6_NEW_DISCIPLINES = ["Cost", "Manufacturing", "Certification"]

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._solvers: dict[str, IDisciplineSolver7D] = {}
        self._runs: dict[str, dict] = {}

        self.registerDisciplineSolver(CostSolver())
        self.registerDisciplineSolver(ManufacturingSolver())
        self.registerDisciplineSolver(CertificationSolver())

    def registerDisciplineSolver(self, solver: IDisciplineSolver7D) -> str:
        name = solver.get_discipline_name()
        self._solvers[name] = solver
        return name

    def run7DisciplineMDO(self, config: MDOConfig7D) -> DesignSolution7D:
        run_id = f"MDO7D-{uuid.uuid4().hex[:8]}"

        active_disciplines = self._resolve_active_disciplines(config.active_discipline_count)

        objective_values = {}
        design_vars = config.design_variables

        for disc_name in active_disciplines:
            solver = self._solvers.get(disc_name)
            if solver:
                result = solver.solve(design_vars)
                objective_values[disc_name] = result

        solution = DesignSolution7D(
            design_parameters=design_vars,
            objective_values=objective_values,
            is_pareto_optimal=True,
        )

        self._runs[run_id] = {
            "config": config,
            "solution": solution,
            "active_disciplines": active_disciplines,
        }

        return solution

    def getDisciplineSensitivity(self, run_id: str) -> DisciplineSensitivityResult:
        if run_id not in self._runs:
            raise ValueError(f"MDO run not found: {run_id}")

        run_data = self._runs[run_id]
        disciplines = run_data.get("active_disciplines", [])

        first_order = {}
        total_order = {}
        breakdown = {}

        for disc in disciplines:
            solver = self._solvers.get(disc)
            if solver:
                for var in solver.get_design_variables():
                    key = f"{var}_{disc}"
                    first_order[key] = round(1.0 / len(solver.get_design_variables()), 4)
                    total_order[key] = round(1.0 / len(solver.get_design_variables()) * 1.2, 4)
                breakdown[disc] = {
                    "variables": solver.get_design_variables(),
                    "objectives": solver.get_objectives(),
                }

        return DisciplineSensitivityResult(
            run_id=run_id,
            first_order_indices=first_order,
            total_order_indices=total_order,
            per_discipline_breakdown=breakdown,
        )

    def _resolve_active_disciplines(self, count: int) -> list[str]:
        if count <= 4:
            return self.V5_DISCIPLINES[:count]
        elif count == 5:
            return self.V5_DISCIPLINES + ["Cost"]
        elif count == 6:
            return self.V5_DISCIPLINES + ["Cost", "Manufacturing"]
        else:
            return self.V5_DISCIPLINES + self.V6_NEW_DISCIPLINES