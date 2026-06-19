import pytest

from services.ai_engine.src.domain.entities.optimization_task import (
    OptimizationTask, OptimizationType, OptimizationStatus, OptimizationAlgorithm,
    ObjectiveFunction, OptimizationConstraint, DesignVariable, ParetoSolution,
)
from services.ai_engine.src.domain.services.multi_objective_optimizer import (
    MultiObjectiveOptimizer, BUILTIN_OBJECTIVES, BUILTIN_CONSTRAINTS, BUILTIN_DESIGN_VARIABLES,
)


class TestOptimizationTaskEntity:
    def test_create_task(self) -> None:
        task = OptimizationTask(project_id="p-001", tenant_id="t-001")
        assert task.status == OptimizationStatus.QUEUED
        assert task.optimization_type == OptimizationType.MULTI_OBJECTIVE
        assert task.id != ""

    def test_start_task(self) -> None:
        task = OptimizationTask(project_id="p-001")
        task.start()
        assert task.status == OptimizationStatus.RUNNING

    def test_cannot_start_running_task(self) -> None:
        task = OptimizationTask(project_id="p-001")
        task.start()
        with pytest.raises(ValueError):
            task.start()

    def test_complete_task(self) -> None:
        task = OptimizationTask(project_id="p-001")
        task.start()
        solutions = [ParetoSolution(
            solution_id="SOL-0001",
            variable_values={"wing_span": 15.0},
            objective_values={"minimize_weight": 100.0},
            constraint_values={"safety_factor": 1.8},
            is_feasible=True,
        )]
        task.complete(solutions, solutions[0])
        assert task.status == OptimizationStatus.COMPLETED
        assert len(task.pareto_front) == 1
        assert task.optimal_solution is not None
        assert task.completed_at != ""
        assert len(task.domain_events) == 1

    def test_fail_task(self) -> None:
        task = OptimizationTask(project_id="p-001")
        task.start()
        task.fail("convergence failed")
        assert task.status == OptimizationStatus.FAILED
        assert task.error_message == "convergence failed"

    def test_task_to_dict(self) -> None:
        task = OptimizationTask(project_id="p-001", tenant_id="t-001")
        d = task.to_dict()
        assert d["project_id"] == "p-001"
        assert d["status"] == "queued"
        assert d["optimization_type"] == "multi_objective"


class TestObjectiveFunction:
    def test_to_dict(self) -> None:
        obj = ObjectiveFunction(name="minimize_weight", direction="minimize", weight=1.0)
        d = obj.to_dict()
        assert d["name"] == "minimize_weight"
        assert d["direction"] == "minimize"


class TestOptimizationConstraint:
    def test_is_satisfied_gte(self) -> None:
        c = OptimizationConstraint(name="safety_factor", operator=">=", value=1.5)
        assert c.is_satisfied(2.0) is True
        assert c.is_satisfied(1.0) is False

    def test_is_satisfied_lte(self) -> None:
        c = OptimizationConstraint(name="max_stress", operator="<=", value=350.0)
        assert c.is_satisfied(300.0) is True
        assert c.is_satisfied(400.0) is False

    def test_is_satisfied_eq(self) -> None:
        c = OptimizationConstraint(name="exact", operator="==", value=5.0)
        assert c.is_satisfied(5.0) is True
        assert c.is_satisfied(5.1) is False


class TestDesignVariable:
    def test_to_dict(self) -> None:
        v = DesignVariable(name="wing_span", lower_bound=5.0, upper_bound=30.0, initial_value=15.0)
        d = v.to_dict()
        assert d["name"] == "wing_span"
        assert d["lower_bound"] == 5.0
        assert d["upper_bound"] == 30.0


class TestParetoSolution:
    def test_to_dict(self) -> None:
        sol = ParetoSolution(
            solution_id="SOL-0001",
            variable_values={"wing_span": 15.0},
            objective_values={"minimize_weight": 100.0},
            constraint_values={"safety_factor": 1.8},
            is_feasible=True,
            rank=0,
        )
        d = sol.to_dict()
        assert d["solution_id"] == "SOL-0001"
        assert d["is_feasible"] is True
        assert d["rank"] == 0


class TestMultiObjectiveOptimizer:
    def test_create_optimization_task(self) -> None:
        optimizer = MultiObjectiveOptimizer()
        task = optimizer.create_optimization_task(
            project_id="p-001",
            tenant_id="t-001",
            objective_names=["minimize_weight", "maximize_lift_drag_ratio"],
            constraint_names=["safety_factor"],
            variable_names=["wing_span", "aspect_ratio"],
        )
        assert task.status == OptimizationStatus.QUEUED
        assert len(task.objectives) == 2
        assert len(task.constraints) == 1
        assert len(task.design_variables) == 2
        assert len(task.domain_events) == 1

    def test_create_task_with_defaults(self) -> None:
        optimizer = MultiObjectiveOptimizer()
        task = optimizer.create_optimization_task(
            project_id="p-001",
            tenant_id="t-001",
            objective_names=[],
            constraint_names=[],
            variable_names=[],
        )
        assert len(task.objectives) == 2
        assert len(task.constraints) == 1
        assert len(task.design_variables) == 2

    def test_run_optimization(self) -> None:
        optimizer = MultiObjectiveOptimizer()
        task = optimizer.create_optimization_task(
            project_id="p-001",
            tenant_id="t-001",
            objective_names=["minimize_weight", "maximize_lift_drag_ratio"],
            constraint_names=["safety_factor"],
            variable_names=["wing_span", "aspect_ratio"],
            max_iterations=5,
            population_size=20,
        )
        result = optimizer.run_optimization(task.id)
        assert result is not None
        assert result.status == OptimizationStatus.COMPLETED
        assert len(result.pareto_front) > 0
        assert result.optimal_solution is not None
        assert result.iteration_count == 5

    def test_run_optimization_task_not_found(self) -> None:
        optimizer = MultiObjectiveOptimizer()
        result = optimizer.run_optimization("nonexistent")
        assert result is None

    def test_get_task(self) -> None:
        optimizer = MultiObjectiveOptimizer()
        task = optimizer.create_optimization_task(
            project_id="p-001", tenant_id="t-001",
            objective_names=["minimize_weight"], constraint_names=["safety_factor"],
            variable_names=["wing_span"],
        )
        found = optimizer.get_task(task.id)
        assert found is not None
        assert found.id == task.id

    def test_list_tasks(self) -> None:
        optimizer = MultiObjectiveOptimizer()
        optimizer.create_optimization_task(
            project_id="p-001", tenant_id="t-001",
            objective_names=["minimize_weight"], constraint_names=[], variable_names=[],
        )
        optimizer.create_optimization_task(
            project_id="p-002", tenant_id="t-001",
            objective_names=["maximize_range"], constraint_names=[], variable_names=[],
        )
        assert len(optimizer.list_tasks()) == 2
        assert len(optimizer.list_tasks("p-001")) == 1

    def test_convergence_history(self) -> None:
        optimizer = MultiObjectiveOptimizer()
        task = optimizer.create_optimization_task(
            project_id="p-001", tenant_id="t-001",
            objective_names=["minimize_weight"],
            constraint_names=["safety_factor"],
            variable_names=["wing_span", "aspect_ratio"],
            max_iterations=3,
            population_size=10,
        )
        result = optimizer.run_optimization(task.id)
        assert len(result.convergence_history) == 3
        for entry in result.convergence_history:
            assert "iteration" in entry
            assert "feasible_count" in entry

    def test_builtin_objectives(self) -> None:
        assert "minimize_weight" in BUILTIN_OBJECTIVES
        assert "maximize_lift_drag_ratio" in BUILTIN_OBJECTIVES
        assert "minimize_cost" in BUILTIN_OBJECTIVES
        assert "maximize_range" in BUILTIN_OBJECTIVES
        assert "maximize_payload" in BUILTIN_OBJECTIVES

    def test_builtin_constraints(self) -> None:
        assert "safety_factor" in BUILTIN_CONSTRAINTS
        assert "min_lift_drag" in BUILTIN_CONSTRAINTS
        assert "max_deformation" in BUILTIN_CONSTRAINTS
        assert "max_stress" in BUILTIN_CONSTRAINTS

    def test_builtin_design_variables(self) -> None:
        assert "wing_span" in BUILTIN_DESIGN_VARIABLES
        assert "aspect_ratio" in BUILTIN_DESIGN_VARIABLES
        assert "wing_sweep_deg" in BUILTIN_DESIGN_VARIABLES
        assert "thickness_ratio" in BUILTIN_DESIGN_VARIABLES
        assert "taper_ratio" in BUILTIN_DESIGN_VARIABLES
        assert "fuselage_length" in BUILTIN_DESIGN_VARIABLES