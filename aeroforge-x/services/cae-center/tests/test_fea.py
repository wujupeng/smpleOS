import pytest

from cae_center.src.domain.entities.fea_task import (
    BCType,
    BoundaryCondition,
    FEAAnalysisType,
    FEAResultSummary,
    FEAStatus,
    FEASolverType,
    FEATask,
    LoadCase,
    LoadType,
    MaterialProperties,
)
from cae_center.src.domain.services.fea_domain_service import FEADomainService, FEAProblemConfig


class TestFEATask:
    def test_create_fea_task(self) -> None:
        task = FEATask(
            model_id="model-001",
            analysis_type=FEAAnalysisType.STRENGTH,
            solver_type=FEASolverType.FENICS,
        )
        assert task.model_id == "model-001"
        assert task.status == FEAStatus.QUEUED
        assert task.analysis_type == FEAAnalysisType.STRENGTH

    def test_state_transitions(self) -> None:
        task = FEATask(model_id="model-001")
        task.start_meshing()
        assert task.status == FEAStatus.MESHING
        task.start_running()
        assert task.status == FEAStatus.RUNNING
        task.start_post_processing()
        assert task.status == FEAStatus.POST_PROCESSING
        result = FEAResultSummary(safety_factor=2.5)
        task.complete(result)
        assert task.status == FEAStatus.COMPLETED
        assert task.progress_percent == 100.0

    def test_invalid_transition(self) -> None:
        task = FEATask(model_id="model-001")
        with pytest.raises(ValueError, match="Cannot start running"):
            task.start_running()

    def test_fail(self) -> None:
        task = FEATask(model_id="model-001")
        task.fail("Solver error")
        assert task.status == FEAStatus.FAILED
        assert task.error_message == "Solver error"

    def test_add_load_case(self) -> None:
        task = FEATask(model_id="model-001")
        lc = LoadCase(name="wing_load", load_type=LoadType.PRESSURE, region="top_surface", values={"magnitude": 50000.0})
        task.add_load_case(lc)
        assert len(task.load_cases) == 1
        assert task.load_cases[0].name == "wing_load"

    def test_add_boundary_condition(self) -> None:
        task = FEATask(model_id="model-001")
        bc = BoundaryCondition(name="root_fixed", bc_type=BCType.FIXED, region="root")
        task.add_boundary_condition(bc)
        assert len(task.boundary_conditions) == 1

    def test_set_material(self) -> None:
        task = FEATask(model_id="model-001")
        mat = MaterialProperties(name="aluminum_7075", elastic_modulus_pa=71.7e9, yield_strength_pa=503e6)
        task.set_material(mat)
        assert task.material_properties is not None
        assert task.material_properties.name == "aluminum_7075"
        assert task.material_properties.elastic_modulus_pa == 71.7e9

    def test_to_dict(self) -> None:
        task = FEATask(model_id="model-001", analysis_type=FEAAnalysisType.FATIGUE)
        d = task.to_dict()
        assert d["model_id"] == "model-001"
        assert d["analysis_type"] == "fatigue"
        assert d["status"] == "queued"

    def test_domain_event_on_complete(self) -> None:
        task = FEATask(model_id="model-001")
        task.start_meshing()
        task.start_running()
        task.start_post_processing()
        task.complete(FEAResultSummary(safety_factor=2.0))
        events = task.domain_events
        assert len(events) == 1
        assert events[0].event_type == "cae.analysis.completed"
        assert events[0].payload["task_type"] == "fea"


class TestLoadCase:
    def test_to_dict(self) -> None:
        lc = LoadCase(name="pressure_load", load_type=LoadType.PRESSURE, region="surface", values={"p": 100000.0})
        d = lc.to_dict()
        assert d["name"] == "pressure_load"
        assert d["load_type"] == "pressure"


class TestBoundaryCondition:
    def test_to_dict(self) -> None:
        bc = BoundaryCondition(name="fixed_root", bc_type=BCType.FIXED, region="root")
        d = bc.to_dict()
        assert d["bc_type"] == "fixed"


class TestMaterialProperties:
    def test_defaults(self) -> None:
        mat = MaterialProperties(name="steel")
        assert mat.elastic_modulus_pa == 200e9
        assert mat.poisson_ratio == 0.3
        assert mat.density_kg_m3 == 7850.0
        assert mat.yield_strength_pa == 250e6

    def test_to_dict(self) -> None:
        mat = MaterialProperties(name="aluminum", elastic_modulus_pa=70e9)
        d = mat.to_dict()
        assert d["name"] == "aluminum"
        assert d["elastic_modulus_pa"] == 70e9


class TestFEAResultSummary:
    def test_to_dict(self) -> None:
        result = FEAResultSummary(
            max_stress_pa=150e6,
            max_deformation_m=0.003,
            safety_factor=1.67,
            fatigue_life_cycles=1e5,
            convergence_status="converged",
        )
        d = result.to_dict()
        assert d["max_stress_pa"] == 150e6
        assert d["safety_factor"] == 1.67


class TestFEAProblemConfig:
    def test_build_problem_definition_strength(self) -> None:
        task = FEATask(model_id="m1", analysis_type=FEAAnalysisType.STRENGTH)
        task.set_material(MaterialProperties(name="steel"))
        task.add_boundary_condition(BoundaryCondition(name="fixed", bc_type=BCType.FIXED, region="root"))
        task.add_load_case(LoadCase(name="pressure", load_type=LoadType.PRESSURE, region="surface"))

        defn = FEAProblemConfig.build_problem_definition(task, "/tmp/mesh.xdmf")
        assert defn["problem_type"] == "linear_elasticity"
        assert len(defn["materials"]) == 1
        assert len(defn["boundary_conditions"]) == 1
        assert len(defn["loads"]) == 1
        assert "displacement" in defn["output_fields"]
        assert "stress" in defn["output_fields"]

    def test_build_problem_definition_fatigue(self) -> None:
        task = FEATask(model_id="m1", analysis_type=FEAAnalysisType.FATIGUE)
        defn = FEAProblemConfig.build_problem_definition(task, "/tmp/mesh.xdmf")
        assert "fatigue_life" in defn["output_fields"]


class TestFEADomainService:
    def setup_method(self) -> None:
        self.service = FEADomainService(working_dir="/tmp/aeroforge/fea_test")

    def test_submit_analysis(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        assert task.status == FEAStatus.QUEUED
        assert task.model_id == "model-001"

    def test_prepare_problem(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        task.set_material(MaterialProperties(name="steel"))
        task.add_boundary_condition(BoundaryCondition(name="fixed", bc_type=BCType.FIXED, region="root"))
        task = self.service.prepare_problem(task, "/tmp/mesh.xdmf")
        assert task.status == FEAStatus.MESHING

    def test_post_process(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        task.set_material(MaterialProperties(name="steel"))
        task = self.service.prepare_problem(task, "/tmp/mesh.xdmf")
        self.service.execute_solver(task, "/tmp/mesh.xdmf")
        task = self.service.post_process(task)
        assert task.status == FEAStatus.COMPLETED
        assert task.result_summary is not None
        assert task.result_summary.safety_factor > 0

    def test_link_to_design_pass(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        task.set_material(MaterialProperties(name="steel"))
        task = self.service.prepare_problem(task, "/tmp/mesh.xdmf")
        self.service.execute_solver(task, "/tmp/mesh.xdmf")
        task = self.service.post_process(task)
        link = self.service.link_to_design(task, min_safety_factor=0.5)
        assert link["linked"] is True
        assert link["meets_target"] is True

    def test_link_to_design_fail_safety(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        task.set_material(MaterialProperties(name="steel"))
        task = self.service.prepare_problem(task, "/tmp/mesh.xdmf")
        self.service.execute_solver(task, "/tmp/mesh.xdmf")
        task = self.service.post_process(task)
        if task.result_summary:
            task.result_summary.safety_factor = 1.0
        link = self.service.link_to_design(task, min_safety_factor=1.5)
        assert link["meets_target"] is False
        assert any(d["metric"] == "safety_factor" for d in link["deviations"])

    def test_get_task(self) -> None:
        task = self.service.submit_analysis(model_id="model-001")
        found = self.service.get_task(task.id)
        assert found is not None

    def test_list_tasks(self) -> None:
        self.service.submit_analysis(model_id="m1")
        self.service.submit_analysis(model_id="m2")
        assert len(self.service.list_tasks()) == 2