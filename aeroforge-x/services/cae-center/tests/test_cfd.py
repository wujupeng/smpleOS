import tempfile
from pathlib import Path

import pytest

from cae_center.src.domain.entities.cfd_task import (
    CFDAnalysisType,
    CFDResultSummary,
    CFDStatus,
    CFDSolverType,
    CFDTask,
    FlightConditions,
    TurbulenceModel,
)
from cae_center.src.domain.services.cfd_domain_service import CFDDomainService, CFDCaseConfig


class TestCFDTask:
    def test_create_cfd_task(self) -> None:
        task = CFDTask(
            model_id="model-001",
            analysis_type=CFDAnalysisType.STEADY,
            solver_type=CFDSolverType.SIMPLE_FOAM,
            turbulence_model=TurbulenceModel.K_OMEGA_SST,
            flight_conditions=FlightConditions(
                altitude_m=3000,
                mach_number=0.3,
                angle_of_attack_deg=5.0,
            ),
        )
        assert task.model_id == "model-001"
        assert task.status == CFDStatus.QUEUED
        assert task.flight_conditions.altitude_m == 3000
        assert task.flight_conditions.mach_number == 0.3

    def test_state_transitions(self) -> None:
        task = CFDTask(model_id="model-001")
        assert task.status == CFDStatus.QUEUED

        task.start_meshing()
        assert task.status == CFDStatus.MESHING

        task.start_running()
        assert task.status == CFDStatus.RUNNING

        task.start_post_processing()
        assert task.status == CFDStatus.POST_PROCESSING

        result = CFDResultSummary(lift_coefficient=0.5, drag_coefficient=0.02)
        task.complete(result)
        assert task.status == CFDStatus.COMPLETED
        assert task.progress_percent == 100.0
        assert task.completed_at is not None

    def test_invalid_transition(self) -> None:
        task = CFDTask(model_id="model-001")
        with pytest.raises(ValueError, match="Cannot start running"):
            task.start_running()

    def test_fail(self) -> None:
        task = CFDTask(model_id="model-001")
        task.fail("Mesh generation error")
        assert task.status == CFDStatus.FAILED
        assert task.error_message == "Mesh generation error"

    def test_update_progress(self) -> None:
        task = CFDTask(model_id="model-001")
        task.update_progress(50.0, "solving")
        assert task.progress_percent == 50.0
        assert task.current_step == "solving"

    def test_to_dict(self) -> None:
        task = CFDTask(
            model_id="model-001",
            flight_conditions=FlightConditions(mach_number=0.5),
        )
        d = task.to_dict()
        assert d["model_id"] == "model-001"
        assert d["status"] == "queued"
        assert d["flight_conditions"]["mach_number"] == 0.5

    def test_domain_event_on_complete(self) -> None:
        task = CFDTask(model_id="model-001")
        task.start_meshing()
        task.start_running()
        task.start_post_processing()
        result = CFDResultSummary(lift_coefficient=0.5, drag_coefficient=0.02)
        task.complete(result)
        events = task.domain_events
        assert len(events) == 1
        assert events[0].event_type == "cae.analysis.completed"

    def test_domain_event_on_fail(self) -> None:
        task = CFDTask(model_id="model-001")
        task.fail("error")
        events = task.domain_events
        assert len(events) == 1
        assert events[0].event_type == "cae.analysis.failed"


class TestFlightConditions:
    def test_to_dict(self) -> None:
        fc = FlightConditions(altitude_m=5000, mach_number=0.8, angle_of_attack_deg=3.0)
        d = fc.to_dict()
        assert d["altitude_m"] == 5000
        assert d["mach_number"] == 0.8
        assert d["angle_of_attack_deg"] == 3.0


class TestCFDResultSummary:
    def test_to_dict(self) -> None:
        result = CFDResultSummary(
            lift_coefficient=0.5,
            drag_coefficient=0.02,
            moment_coefficient=0.1,
            convergence_status="converged",
            lift_to_drag_ratio=25.0,
        )
        d = result.to_dict()
        assert d["lift_coefficient"] == 0.5
        assert d["drag_coefficient"] == 0.02
        assert d["lift_to_drag_ratio"] == 25.0


class TestCFDCaseConfig:
    def test_build_control_dict_steady(self) -> None:
        task = CFDTask(model_id="m1", analysis_type=CFDAnalysisType.STEADY)
        config = CFDCaseConfig.build_control_dict(task)
        assert config["application"] == "simpleFoam"
        assert config["endTime"] == 1000

    def test_build_control_dict_unsteady(self) -> None:
        task = CFDTask(
            model_id="m1",
            analysis_type=CFDAnalysisType.UNSTEADY,
            solver_type=CFDSolverType.PIMPLE_FOAM,
        )
        config = CFDCaseConfig.build_control_dict(task)
        assert config["application"] == "pimpleFoam"
        assert config["deltaT"] == 1e-4

    def test_build_fv_schemes_steady(self) -> None:
        task = CFDTask(model_id="m1", analysis_type=CFDAnalysisType.STEADY)
        config = CFDCaseConfig.build_fv_schemes(task)
        assert config["ddtSchemes"]["default"] == "steadyState"

    def test_build_fv_schemes_unsteady(self) -> None:
        task = CFDTask(model_id="m1", analysis_type=CFDAnalysisType.UNSTEADY)
        config = CFDCaseConfig.build_fv_schemes(task)
        assert config["ddtSchemes"]["default"] == "Euler"

    def test_build_fv_solution(self) -> None:
        task = CFDTask(model_id="m1")
        config = CFDCaseConfig.build_fv_solution(task)
        assert "solvers" in config
        assert "SIMPLE" in config
        assert "relaxationFactors" in config

    def test_build_turbulence_properties(self) -> None:
        task = CFDTask(model_id="m1", turbulence_model=TurbulenceModel.K_OMEGA_SST)
        config = CFDCaseConfig.build_turbulence_properties(task)
        assert config["RAS"]["model"] == "kOmegaSST"

    def test_build_boundary_conditions(self) -> None:
        task = CFDTask(model_id="m1", flight_conditions=FlightConditions(mach_number=0.3))
        bc = CFDCaseConfig.build_boundary_conditions(task)
        assert "U" in bc
        assert "p" in bc


class TestCFDDomainService:
    def setup_method(self) -> None:
        self.service = CFDDomainService(working_dir=tempfile.mkdtemp())

    def test_submit_analysis(self) -> None:
        task = self.service.submit_analysis(
            model_id="model-001",
            analysis_type=CFDAnalysisType.STEADY,
            flight_conditions=FlightConditions(mach_number=0.3),
        )
        assert task.status == CFDStatus.QUEUED
        assert task.model_id == "model-001"

    def test_prepare_case(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        case_dir = tempfile.mkdtemp()
        task = self.service.prepare_case(task, case_dir)
        assert task.status == CFDStatus.MESHING
        assert task.case_dir == case_dir
        assert (Path(case_dir) / "system" / "controlDict").exists()
        assert (Path(case_dir) / "system" / "fvSchemes").exists()
        assert (Path(case_dir) / "system" / "fvSolution").exists()
        assert (Path(case_dir) / "constant" / "turbulenceProperties").exists()

    def test_post_process(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        case_dir = tempfile.mkdtemp()
        task = self.service.prepare_case(task, case_dir)
        task.start_running()
        task = self.service.post_process(task)
        assert task.status == CFDStatus.COMPLETED
        assert task.result_summary is not None

    def test_link_to_design_no_deviations(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        case_dir = tempfile.mkdtemp()
        task = self.service.prepare_case(task, case_dir)
        task.start_running()
        task = self.service.post_process(task)
        link = self.service.link_to_design(task, design_target_ld=0.0)
        assert link["linked"] is True
        assert link["meets_target"] is True

    def test_link_to_design_with_deviations(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        case_dir = tempfile.mkdtemp()
        task = self.service.prepare_case(task, case_dir)
        task.start_running()
        task = self.service.post_process(task)
        if task.result_summary:
            task.result_summary.lift_to_drag_ratio = 5.0
            task.result_summary.drag_coefficient = 0.08
        link = self.service.link_to_design(task, design_target_ld=10.0)
        assert link["linked"] is True
        assert link["meets_target"] is False
        assert len(link["deviations"]) == 2

    def test_get_task(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        found = self.service.get_task(task.id)
        assert found is not None
        assert found.id == task.id

    def test_list_tasks(self) -> None:
        self.service.submit_analysis(model_id="model-001")
        self.service.submit_analysis(model_id="model-002")
        tasks = self.service.list_tasks()
        assert len(tasks) == 2