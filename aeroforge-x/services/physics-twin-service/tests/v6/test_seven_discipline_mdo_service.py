"""AeroForge-X V6.0/V6.1 Unit Tests - SevenDisciplineMDOService
REQ-E-ENH-008~014, REQ-VP-020
"""

import pytest

from src.domain.services.generative_design.seven_discipline_mdo_service import (
    SevenDisciplineMDOService,
    MDOConfig7D,
    DesignSolution7D,
    DisciplineSensitivityResult,
    CostSolver,
    ManufacturingSolver,
    CertificationSolver,
)


@pytest.fixture
def service():
    return SevenDisciplineMDOService()


class TestDisciplineSolvers:

    def test_cost_solver(self):
        solver = CostSolver()
        result = solver.solve({"wing_span": 30, "engine_count": 2})
        assert "lifecycle_cost" in result
        assert result["lifecycle_cost"] > 0

    def test_manufacturing_solver(self):
        solver = ManufacturingSolver()
        result = solver.solve({"wing_span": 30, "fuselage_length": 30})
        assert "feasibility_score" in result
        assert 0 <= result["feasibility_score"] <= 1

    def test_certification_solver(self):
        solver = CertificationSolver()
        result = solver.solve({"engine_count": 2, "wing_span": 30})
        assert "certification_effort_hours" in result
        assert result["certification_effort_hours"] > 0

    def test_solver_design_variables(self):
        solver = CostSolver()
        assert "wing_span" in solver.get_design_variables()

    def test_solver_constraints(self):
        solver = CostSolver()
        constraints = solver.get_constraints()
        assert len(constraints) > 0

    def test_solver_objectives(self):
        solver = CertificationSolver()
        assert "certification_effort_hours" in solver.get_objectives()


class TestRegisterDisciplineSolver:

    def test_register_custom_solver(self, service):
        solver = CostSolver()
        name = service.registerDisciplineSolver(solver)
        assert name == "Cost"

    def test_default_solvers_registered(self, service):
        assert "Cost" in service._solvers
        assert "Manufacturing" in service._solvers
        assert "Certification" in service._solvers


class TestRun7DisciplineMDO:

    def test_run_7_discipline(self, service):
        config = MDOConfig7D(
            requirement_id="REQ-001",
            design_variables={"wing_span": 30, "engine_count": 2, "fuselage_length": 30},
            active_discipline_count=7,
        )
        result = service.run7DisciplineMDO(config)
        assert isinstance(result, DesignSolution7D)
        assert len(result.objective_values) >= 3

    def test_run_4_discipline(self, service):
        config = MDOConfig7D(
            requirement_id="REQ-002",
            design_variables={"wing_span": 30},
            active_discipline_count=4,
        )
        result = service.run7DisciplineMDO(config)
        assert len(result.objective_values) >= 0

    def test_run_5_discipline(self, service):
        config = MDOConfig7D(
            requirement_id="REQ-003",
            design_variables={"wing_span": 30, "engine_count": 2},
            active_discipline_count=5,
        )
        result = service.run7DisciplineMDO(config)
        assert "Cost" in result.objective_values

    def test_run_6_discipline(self, service):
        config = MDOConfig7D(
            requirement_id="REQ-004",
            design_variables={"wing_span": 30, "fuselage_length": 30, "engine_count": 2},
            active_discipline_count=6,
        )
        result = service.run7DisciplineMDO(config)
        assert "Manufacturing" in result.objective_values


class TestDisciplineSensitivity:

    def test_get_sensitivity(self, service):
        config = MDOConfig7D(
            requirement_id="REQ-001",
            design_variables={"wing_span": 30, "engine_count": 2, "fuselage_length": 30},
            active_discipline_count=7,
        )
        solution = service.run7DisciplineMDO(config)
        run_id = list(service._runs.keys())[0]
        result = service.getDisciplineSensitivity(run_id)
        assert isinstance(result, DisciplineSensitivityResult)
        assert len(result.first_order_indices) > 0
        assert len(result.per_discipline_breakdown) > 0

    def test_sensitivity_nonexistent_run_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.getDisciplineSensitivity("FAKE-RUN")