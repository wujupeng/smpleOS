import pytest
from unittest.mock import MagicMock, patch

from cae_center.src.infrastructure.celery_tasks.cae_tasks import (
    CAEBaseTask,
    TaskCallback,
    TaskPriority,
    TaskProgress,
    TaskStatus,
)
from cae_center.src.infrastructure.celery_tasks.cfd_tasks import CFDTaskHandler
from cae_center.src.infrastructure.celery_tasks.fea_tasks import FEATaskHandler
from cae_center.src.infrastructure.celery_tasks.flutter_tasks import FlutterTaskHandler
from cae_center.src.infrastructure.celery_tasks.thermal_tasks import ThermalTaskHandler
from cae_center.src.infrastructure.celery_tasks.multiphysics_tasks import MultiphysicsTaskHandler


class TestTaskPriority:
    def test_priority_values(self) -> None:
        assert TaskPriority.URGENT == 0
        assert TaskPriority.HIGH == 1
        assert TaskPriority.NORMAL == 2
        assert TaskPriority.LOW == 3


class TestTaskStatus:
    def test_status_values(self) -> None:
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.STARTED == "started"
        assert TaskStatus.PROGRESS == "progress"
        assert TaskStatus.SUCCESS == "success"
        assert TaskStatus.FAILURE == "failure"
        assert TaskStatus.RETRY == "retry"
        assert TaskStatus.REVOKED == "revoked"


class TestTaskProgress:
    def test_defaults(self) -> None:
        p = TaskProgress()
        assert p.percent == 0.0
        assert p.current_step == ""
        assert p.details == {}


class TestTaskCallback:
    def test_creation(self) -> None:
        cb = TaskCallback(
            event_type="cae.task.status_changed",
            task_id="test-123",
            status=TaskStatus.SUCCESS,
        )
        assert cb.event_type == "cae.task.status_changed"
        assert cb.task_id == "test-123"
        assert cb.progress is None
        assert cb.result is None
        assert cb.error is None


class TestCFDTaskHandler:
    def setup_method(self) -> None:
        self.handler = CFDTaskHandler()

    def test_task_type(self) -> None:
        assert self.handler.task_type == "cfd"

    def test_execute(self) -> None:
        result = self.handler.execute("test-cfd-1", {
            "case_dir": "/tmp/case",
            "solver": "simpleFoam",
            "n_proc": 4,
        })
        assert result["task_type"] == "cfd"
        assert result["solver"] == "simpleFoam"
        assert "lift_coefficient" in result
        assert "drag_coefficient" in result
        assert "convergence_status" in result

    def test_time_limits(self) -> None:
        assert self.handler.soft_time_limit == 7200
        assert self.handler.time_limit == 14400


class TestFEATaskHandler:
    def setup_method(self) -> None:
        self.handler = FEATaskHandler()

    def test_task_type(self) -> None:
        assert self.handler.task_type == "fea"

    def test_execute(self) -> None:
        result = self.handler.execute("test-fea-1", {
            "problem_type": "linear_elasticity",
        })
        assert result["task_type"] == "fea"
        assert result["problem_type"] == "linear_elasticity"
        assert "max_stress" in result
        assert "max_displacement" in result
        assert "safety_factor" in result


class TestFlutterTaskHandler:
    def setup_method(self) -> None:
        self.handler = FlutterTaskHandler()

    def test_task_type(self) -> None:
        assert self.handler.task_type == "flutter"

    def test_execute(self) -> None:
        result = self.handler.execute("test-flutter-1", {
            "n_modes": 10,
        })
        assert result["task_type"] == "flutter"
        assert "flutter_speed" in result
        assert "flutter_frequency" in result
        assert "divergence_speed" in result


class TestThermalTaskHandler:
    def setup_method(self) -> None:
        self.handler = ThermalTaskHandler()

    def test_task_type(self) -> None:
        assert self.handler.task_type == "thermal"

    def test_execute(self) -> None:
        result = self.handler.execute("test-thermal-1", {
            "analysis_type": "steady_state",
        })
        assert result["task_type"] == "thermal"
        assert "max_temperature" in result
        assert "min_temperature" in result
        assert "heat_flux_max" in result


class TestMultiphysicsTaskHandler:
    def setup_method(self) -> None:
        self.handler = MultiphysicsTaskHandler()

    def test_task_type(self) -> None:
        assert self.handler.task_type == "multiphysics"

    def test_execute_weak_coupling(self) -> None:
        result = self.handler.execute("test-multi-1", {
            "coupling_type": "weak",
        })
        assert result["task_type"] == "multiphysics"
        assert result["coupling_type"] == "weak"
        assert "thermal_results" in result
        assert "structural_results" in result

    def test_execute_strong_coupling(self) -> None:
        result = self.handler.execute("test-multi-2", {
            "coupling_type": "strong",
            "coupling_iterations": 3,
        })
        assert result["coupling_type"] == "strong"
        assert result["converged"] is True

    def test_time_limits(self) -> None:
        assert self.handler.soft_time_limit == 10800
        assert self.handler.time_limit == 21600