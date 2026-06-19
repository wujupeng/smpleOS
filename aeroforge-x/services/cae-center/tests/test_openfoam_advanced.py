from __future__ import annotations

import pytest

from src.domain.entities.openfoam_advanced import (
    ParametricStudy, SweepRange, CaseResult, ParametricStudyStatus,
    AdjointOptimization, AdjointIteration, AdjointOptStatus,
    AeroDatabase, AeroDatabasePoint, AeroDatabaseStatus,
)
from src.domain.services.openfoam_advanced_service import OpenFOAMAdvancedService


class TestParametricStudy:
    def test_sweep_range_to_points(self):
        sr = SweepRange(parameter="angle_of_attack", start=0, end=10, step=2, unit="deg")
        points = sr.to_points()
        assert len(points) == 6
        assert points[0] == 0
        assert points[-1] == 10

    def test_calculate_total_cases(self):
        study = ParametricStudy(
            model_id="m1",
            sweep_ranges=[
                SweepRange(parameter="angle_of_attack", start=0, end=5, step=1, unit="deg"),
                SweepRange(parameter="mach_number", start=0.1, end=0.3, step=0.1),
            ],
        )
        total = study.calculate_total_cases()
        assert total == 6 * 3

    def test_add_case_result(self):
        study = ParametricStudy(model_id="m1")
        result = CaseResult(case_id="c1", parameters={"alpha": 5}, lift_coefficient=0.5,
                            drag_coefficient=0.02, convergence_status="converged")
        study.add_case_result(result)
        assert study.completed_cases == 1
        assert len(study.case_results) == 1

    def test_complete_study(self):
        study = ParametricStudy(model_id="m1")
        study.complete_study()
        assert study.status == ParametricStudyStatus.COMPLETED
        assert study.completed_at is not None

    def test_fail_study(self):
        study = ParametricStudy(model_id="m1")
        study.fail("error")
        assert study.status == ParametricStudyStatus.FAILED
        assert study.error_message == "error"


class TestAdjointOptimization:
    def test_add_iteration(self):
        opt = AdjointOptimization(model_id="m1")
        iteration = AdjointIteration(iteration=1, objective_value=0.05,
                                     sensitivity_norm=0.01, geometry_update_norm=0.001)
        opt.add_iteration(iteration)
        assert opt.current_iteration == 1
        assert len(opt.iterations) == 1

    def test_complete_optimization(self):
        opt = AdjointOptimization(model_id="m1")
        opt.add_iteration(AdjointIteration(iteration=1, objective_value=0.05,
                                           sensitivity_norm=0.01, geometry_update_norm=0.001))
        opt.add_iteration(AdjointIteration(iteration=2, objective_value=0.04,
                                           sensitivity_norm=0.005, geometry_update_norm=0.0005))
        opt.complete()
        assert opt.status == AdjointOptStatus.COMPLETED
        assert opt.initial_objective == 0.05
        assert opt.final_objective == 0.04
        assert opt.improvement_pct > 0

    def test_to_dict(self):
        opt = AdjointOptimization(model_id="m1")
        d = opt.to_dict()
        assert d["model_id"] == "m1"
        assert d["status"] == "queued"


class TestAeroDatabase:
    def test_calculate_total_points(self):
        db = AeroDatabase(
            model_id="m1",
            alpha_range=SweepRange("angle_of_attack", -5, 5, 1, "deg"),
            mach_range=SweepRange("mach_number", 0.1, 0.3, 0.1),
            beta_range=SweepRange("sideslip_angle", -5, 5, 5, "deg"),
        )
        total = db.calculate_total_points()
        assert total == 11 * 3 * 3

    def test_add_data_point(self):
        db = AeroDatabase(model_id="m1")
        point = AeroDatabasePoint(angle_of_attack=5, mach_number=0.3, sideslip_angle=0,
                                  cl=0.5, cd=0.02, cm=-0.05)
        db.add_data_point(point)
        assert db.completed_points == 1
        assert len(db.data_points) == 1

    def test_complete_database(self):
        db = AeroDatabase(model_id="m1")
        db.complete()
        assert db.status == AeroDatabaseStatus.COMPLETED


class TestOpenFOAMAdvancedService:
    def setup_method(self):
        self.service = OpenFOAMAdvancedService()

    def test_run_parametric_study(self):
        study = self.service.run_parametric_study(
            model_id="m1",
            project_id="p1",
            tenant_id="t1",
            sweep_ranges=[
                {"parameter": "angle_of_attack", "start": 0, "end": 5, "step": 1, "unit": "deg"},
                {"parameter": "mach_number", "start": 0.1, "end": 0.3, "step": 0.1},
            ],
        )
        assert study.status == ParametricStudyStatus.COMPLETED
        assert study.total_cases == 6 * 3
        assert len(study.case_results) == study.total_cases

    def test_run_adjoint_optimization(self):
        opt = self.service.run_adjoint_optimization(
            model_id="m1",
            project_id="p1",
            tenant_id="t1",
            max_iterations=5,
        )
        assert opt.status == AdjointOptStatus.COMPLETED
        assert len(opt.iterations) == 5
        assert opt.improvement_pct > 0

    def test_generate_aero_database(self):
        db = self.service.generate_aero_database(
            model_id="m1",
            project_id="p1",
            tenant_id="t1",
            alpha_range={"parameter": "angle_of_attack", "start": 0, "end": 5, "step": 5, "unit": "deg"},
            mach_range={"parameter": "mach_number", "start": 0.1, "end": 0.2, "step": 0.1},
            beta_range={"parameter": "sideslip_angle", "start": 0, "end": 0, "step": 1, "unit": "deg"},
        )
        assert db.status == AeroDatabaseStatus.COMPLETED
        assert len(db.data_points) > 0