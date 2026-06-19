from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ProblemType(str, Enum):
    LINEAR_ELASTICITY = "linear_elasticity"
    THERMAL = "thermal"
    MODAL = "modal"
    BUCKLING = "buckling"
    NONLINEAR_ELASTICITY = "nonlinear_elasticity"
    COUPLED_THERMO_MECHANICAL = "coupled_thermo_mechanical"


class BoundaryConditionType(str, Enum):
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"
    ROBIN = "robin"
    PERIODIC = "periodic"


@dataclass
class BoundaryCondition:
    name: str
    bc_type: BoundaryConditionType
    region: str
    values: dict[str, float] = field(default_factory=dict)


@dataclass
class LoadCondition:
    name: str
    load_type: str
    region: str
    values: dict[str, float] = field(default_factory=dict)


@dataclass
class MaterialProperty:
    name: str
    properties: dict[str, float] = field(default_factory=dict)


@dataclass
class ProblemDefinition:
    problem_type: ProblemType
    mesh_path: str
    materials: list[MaterialProperty] = field(default_factory=list)
    boundary_conditions: list[BoundaryCondition] = field(default_factory=list)
    loads: list[LoadCondition] = field(default_factory=list)
    solver_params: dict[str, Any] = field(default_factory=dict)
    output_fields: list[str] = field(default_factory=list)


class ProblemBuilder:
    def __init__(self) -> None:
        self._problem_type: ProblemType | None = None
        self._mesh_path: str = ""
        self._materials: list[MaterialProperty] = []
        self._boundary_conditions: list[BoundaryCondition] = []
        self._loads: list[LoadCondition] = []
        self._solver_params: dict[str, Any] = {}
        self._output_fields: list[str] = []

    def set_problem_type(self, problem_type: ProblemType) -> ProblemBuilder:
        self._problem_type = problem_type
        return self

    def set_mesh(self, mesh_path: str) -> ProblemBuilder:
        self._mesh_path = mesh_path
        return self

    def add_material(self, name: str, properties: dict[str, float]) -> ProblemBuilder:
        self._materials.append(MaterialProperty(name=name, properties=properties))
        return self

    def add_boundary_condition(
        self,
        name: str,
        bc_type: BoundaryConditionType,
        region: str,
        values: dict[str, float] | None = None,
    ) -> ProblemBuilder:
        self._boundary_conditions.append(
            BoundaryCondition(name=name, bc_type=bc_type, region=region, values=values or {})
        )
        return self

    def add_load(
        self,
        name: str,
        load_type: str,
        region: str,
        values: dict[str, float] | None = None,
    ) -> ProblemBuilder:
        self._loads.append(
            LoadCondition(name=name, load_type=load_type, region=region, values=values or {})
        )
        return self

    def set_solver_params(self, params: dict[str, Any]) -> ProblemBuilder:
        self._solver_params = params
        return self

    def add_output_field(self, field_name: str) -> ProblemBuilder:
        self._output_fields.append(field_name)
        return self

    def build(self) -> ProblemDefinition:
        if self._problem_type is None:
            raise ValueError("Problem type must be set")
        if not self._mesh_path:
            raise ValueError("Mesh path must be set")

        default_outputs = self._default_output_fields(self._problem_type)
        output_fields = self._output_fields or default_outputs

        problem = ProblemDefinition(
            problem_type=self._problem_type,
            mesh_path=self._mesh_path,
            materials=list(self._materials),
            boundary_conditions=list(self._boundary_conditions),
            loads=list(self._loads),
            solver_params=dict(self._solver_params),
            output_fields=output_fields,
        )

        logger.info(
            "Built FEniCS problem: type=%s mesh=%s bcs=%d loads=%d",
            problem.problem_type.value, problem.mesh_path,
            len(problem.boundary_conditions), len(problem.loads),
        )

        self._reset()
        return problem

    def _reset(self) -> None:
        self._problem_type = None
        self._mesh_path = ""
        self._materials.clear()
        self._boundary_conditions.clear()
        self._loads.clear()
        self._solver_params.clear()
        self._output_fields.clear()

    @staticmethod
    def _default_output_fields(problem_type: ProblemType) -> list[str]:
        defaults: dict[ProblemType, list[str]] = {
            ProblemType.LINEAR_ELASTICITY: ["displacement", "stress", "strain"],
            ProblemType.THERMAL: ["temperature", "heat_flux"],
            ProblemType.MODAL: ["eigenvalues", "eigenvectors"],
            ProblemType.BUCKLING: ["buckling_load", "buckling_mode"],
            ProblemType.NONLINEAR_ELASTICITY: ["displacement", "stress", "strain"],
            ProblemType.COUPLED_THERMO_MECHANICAL: [
                "displacement", "stress", "temperature", "heat_flux",
            ],
        }
        return defaults.get(problem_type, [])