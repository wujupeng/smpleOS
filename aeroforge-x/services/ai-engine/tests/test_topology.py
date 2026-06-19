import pytest

from services.ai_engine.src.domain.entities.topology_task import (
    TopologyOptimizationTask, TopologyMethod, TopologyStatus,
    LoadCase, LoadCaseType, BoundaryCondition, DesignRegion, TopologyResult,
)
from services.ai_engine.src.domain.services.topology_optimizer import (
    TopologyOptimizer, BUILTIN_LOAD_CASES, BUILTIN_BOUNDARY_CONDITIONS, BUILTIN_DESIGN_REGIONS,
)


class TestTopologyTaskEntity:
    def test_create_task(self) -> None:
        task = TopologyOptimizationTask(project_id="p-001", tenant_id="t-001")
        assert task.status == TopologyStatus.QUEUED
        assert task.method == TopologyMethod.SIMP
        assert task.id != ""

    def test_lifecycle_transitions(self) -> None:
        task = TopologyOptimizationTask(project_id="p-001")
        task.start_meshing()
        assert task.status == TopologyStatus.MESHING
        task.start_optimization()
        assert task.status == TopologyStatus.OPTIMIZING
        task.start_post_processing()
        assert task.status == TopologyStatus.POST_PROCESSING
        result = TopologyResult(iteration_count=10, mass_reduction_pct=45.0, converged=True)
        task.complete(result)
        assert task.status == TopologyStatus.COMPLETED
        assert task.result is not None
        assert task.result.mass_reduction_pct == 45.0
        assert len(task.domain_events) == 1

    def test_cannot_skip_meshing(self) -> None:
        task = TopologyOptimizationTask(project_id="p-001")
        with pytest.raises(ValueError):
            task.start_optimization()

    def test_fail_task(self) -> None:
        task = TopologyOptimizationTask(project_id="p-001")
        task.start_meshing()
        task.fail("mesh generation failed")
        assert task.status == TopologyStatus.FAILED
        assert task.error_message == "mesh generation failed"

    def test_task_to_dict(self) -> None:
        task = TopologyOptimizationTask(project_id="p-001", tenant_id="t-001")
        d = task.to_dict()
        assert d["project_id"] == "p-001"
        assert d["status"] == "queued"
        assert d["method"] == "simp"


class TestLoadCase:
    def test_to_dict(self) -> None:
        lc = LoadCase(name="wing_bending", load_case_type=LoadCaseType.BENDING, force_z=-5000.0)
        d = lc.to_dict()
        assert d["name"] == "wing_bending"
        assert d["force_z"] == -5000.0
        assert d["load_case_type"] == "bending"


class TestBoundaryCondition:
    def test_to_dict(self) -> None:
        bc = BoundaryCondition(name="wing_root_fixed", constrained_dofs=["x", "y", "z"])
        d = bc.to_dict()
        assert d["name"] == "wing_root_fixed"
        assert d["constrained_dofs"] == ["x", "y", "z"]


class TestDesignRegion:
    def test_to_dict(self) -> None:
        dr = DesignRegion(name="wing_box", volume_fraction=0.3, min_member_size=3.0)
        d = dr.to_dict()
        assert d["name"] == "wing_box"
        assert d["volume_fraction"] == 0.3


class TestTopologyResult:
    def test_to_dict(self) -> None:
        result = TopologyResult(
            iteration_count=20, final_volume_fraction=0.28,
            compliance=0.005, max_stress=280.0,
            mass_reduction_pct=72.0, converged=True,
        )
        d = result.to_dict()
        assert d["iteration_count"] == 20
        assert d["mass_reduction_pct"] == 72.0
        assert d["converged"] is True


class TestTopologyOptimizer:
    def test_create_topology_task(self) -> None:
        optimizer = TopologyOptimizer()
        task = optimizer.create_topology_task(
            project_id="p-001",
            tenant_id="t-001",
            design_region_names=["wing_box"],
            load_case_names=["wing_bending"],
            boundary_condition_names=["wing_root_fixed"],
        )
        assert task.status == TopologyStatus.QUEUED
        assert len(task.design_regions) == 1
        assert len(task.load_cases) == 1
        assert len(task.boundary_conditions) == 1
        assert len(task.domain_events) == 1

    def test_create_task_with_defaults(self) -> None:
        optimizer = TopologyOptimizer()
        task = optimizer.create_topology_task(
            project_id="p-001",
            tenant_id="t-001",
            design_region_names=[],
            load_case_names=[],
            boundary_condition_names=[],
        )
        assert len(task.design_regions) == 1
        assert len(task.load_cases) == 1
        assert len(task.boundary_conditions) == 1

    def test_run_topology_optimization(self) -> None:
        optimizer = TopologyOptimizer()
        task = optimizer.create_topology_task(
            project_id="p-001",
            tenant_id="t-001",
            design_region_names=["wing_box"],
            load_case_names=["wing_bending"],
            boundary_condition_names=["wing_root_fixed"],
            max_iterations=5,
        )
        result = optimizer.run_topology_optimization(task.id)
        assert result is not None
        assert result.status == TopologyStatus.COMPLETED
        assert result.result is not None
        assert result.result.mass_reduction_pct > 0
        assert len(result.iteration_history) > 0

    def test_run_topology_task_not_found(self) -> None:
        optimizer = TopologyOptimizer()
        result = optimizer.run_topology_optimization("nonexistent")
        assert result is None

    def test_get_task(self) -> None:
        optimizer = TopologyOptimizer()
        task = optimizer.create_topology_task(
            project_id="p-001", tenant_id="t-001",
            design_region_names=["wing_box"], load_case_names=["wing_bending"],
            boundary_condition_names=["wing_root_fixed"],
        )
        found = optimizer.get_task(task.id)
        assert found is not None
        assert found.id == task.id

    def test_list_tasks(self) -> None:
        optimizer = TopologyOptimizer()
        optimizer.create_topology_task(
            project_id="p-001", tenant_id="t-001",
            design_region_names=["wing_box"], load_case_names=[], boundary_condition_names=[],
        )
        optimizer.create_topology_task(
            project_id="p-002", tenant_id="t-001",
            design_region_names=["fuselage_frame"], load_case_names=[], boundary_condition_names=[],
        )
        assert len(optimizer.list_tasks()) == 2
        assert len(optimizer.list_tasks("p-001")) == 1

    def test_iteration_history(self) -> None:
        optimizer = TopologyOptimizer()
        task = optimizer.create_topology_task(
            project_id="p-001", tenant_id="t-001",
            design_region_names=["wing_box"], load_case_names=["wing_bending"],
            boundary_condition_names=["wing_root_fixed"],
            max_iterations=3,
        )
        result = optimizer.run_topology_optimization(task.id)
        assert len(result.iteration_history) > 0
        for entry in result.iteration_history:
            assert "iteration" in entry
            assert "compliance" in entry
            assert "volume_fraction" in entry

    def test_builtin_load_cases(self) -> None:
        assert "wing_bending" in BUILTIN_LOAD_CASES
        assert "wing_torsion" in BUILTIN_LOAD_CASES
        assert "fuselage_compression" in BUILTIN_LOAD_CASES
        assert "landing_impact" in BUILTIN_LOAD_CASES
        assert "gust_load" in BUILTIN_LOAD_CASES

    def test_builtin_boundary_conditions(self) -> None:
        assert "wing_root_fixed" in BUILTIN_BOUNDARY_CONDITIONS
        assert "fuselage_support" in BUILTIN_BOUNDARY_CONDITIONS
        assert "symmetry_plane" in BUILTIN_BOUNDARY_CONDITIONS

    def test_builtin_design_regions(self) -> None:
        assert "wing_box" in BUILTIN_DESIGN_REGIONS
        assert "fuselage_frame" in BUILTIN_DESIGN_REGIONS
        assert "rib_structure" in BUILTIN_DESIGN_REGIONS
        assert "landing_gear_mount" in BUILTIN_DESIGN_REGIONS

    def test_level_set_method(self) -> None:
        optimizer = TopologyOptimizer()
        task = optimizer.create_topology_task(
            project_id="p-001", tenant_id="t-001",
            design_region_names=["wing_box"], load_case_names=["wing_bending"],
            boundary_condition_names=["wing_root_fixed"],
            method=TopologyMethod.LEVEL_SET,
            max_iterations=3,
        )
        result = optimizer.run_topology_optimization(task.id)
        assert result.status == TopologyStatus.COMPLETED

    def test_beso_method(self) -> None:
        optimizer = TopologyOptimizer()
        task = optimizer.create_topology_task(
            project_id="p-001", tenant_id="t-001",
            design_region_names=["fuselage_frame"], load_case_names=["fuselage_compression"],
            boundary_condition_names=["fuselage_support"],
            method=TopologyMethod.BESO,
            max_iterations=3,
        )
        result = optimizer.run_topology_optimization(task.id)
        assert result.status == TopologyStatus.COMPLETED