from __future__ import annotations

import pytest

from src.domain.entities.fenics_advanced import (
    CustomFEATask, UFLDefinition, FEASolutionField, CustomFEAStatus,
    FatigueAnalysisTask, RainflowCycle, FatigueDamageResult, MeanStressCorrection,
    BucklingAnalysisTask, BucklingMode, BucklingAnalysisStatus,
)
from src.domain.services.fenics_advanced_service import FEniCSAdvancedService


class TestCustomFEA:
    def test_create_task(self):
        task = CustomFEATask(model_id="m1", ufl_definition=UFLDefinition(filename="test.ufl", content="a = 1"))
        assert task.status == CustomFEAStatus.QUEUED

    def test_complete_task(self):
        task = CustomFEATask(model_id="m1")
        fields = [FEASolutionField(name="displacement", min_val=0, max_val=1)]
        task.complete(fields, solve_time=2.5)
        assert task.status == CustomFEAStatus.COMPLETED
        assert task.solve_time_seconds == 2.5

    def test_fail_task(self):
        task = CustomFEATask(model_id="m1")
        task.fail("parse error")
        assert task.status == CustomFEAStatus.FAILED


class TestFatigueAnalysis:
    def test_rainflow_counting(self):
        service = FEniCSAdvancedService()
        spectrum = [0, 100, -50, 80, -30, 60, 0]
        cycles = service._rainflow_counting(spectrum)
        assert len(cycles) > 0

    def test_interpolate_sn_curve(self):
        service = FEniCSAdvancedService()
        sn = service._default_sn_curve()
        n = service._interpolate_sn_curve(400, sn, 1e7)
        assert n > 0
        assert 1e4 < n < 1e5

    def test_full_fatigue_analysis(self):
        service = FEniCSAdvancedService()
        spectrum = [0, 100, -50, 80, -30, 60, 0, 90, -40, 70, 0]
        task = service.run_fatigue_analysis(
            model_id="m1",
            project_id="p1",
            tenant_id="t1",
            load_spectrum=spectrum,
            mean_stress_correction=MeanStressCorrection.GOODMAN,
        )
        assert task.status.value == "completed"
        assert len(task.rainflow_cycles) > 0
        assert len(task.damage_results) > 0
        assert task.total_damage > 0

    def test_mean_stress_goodman(self):
        service = FEniCSAdvancedService()
        spectrum = [0, 200, 0, 200, 0]
        task = service.run_fatigue_analysis(
            model_id="m1", project_id="p1", tenant_id="t1",
            load_spectrum=spectrum,
            mean_stress_correction=MeanStressCorrection.GOODMAN,
        )
        assert task.status.value == "completed"

    def test_mean_stress_gerber(self):
        service = FEniCSAdvancedService()
        spectrum = [0, 200, 0, 200, 0]
        task = service.run_fatigue_analysis(
            model_id="m1", project_id="p1", tenant_id="t1",
            load_spectrum=spectrum,
            mean_stress_correction=MeanStressCorrection.GERBER,
        )
        assert task.status.value == "completed"


class TestBucklingAnalysis:
    def test_run_buckling(self):
        service = FEniCSAdvancedService()
        task = service.run_buckling_analysis(
            model_id="m1", project_id="p1", tenant_id="t1", num_modes=5,
        )
        assert task.status == BucklingAnalysisStatus.COMPLETED
        assert len(task.buckling_modes) == 5
        assert task.critical_load_factor > 0

    def test_modes_ordered(self):
        service = FEniCSAdvancedService()
        task = service.run_buckling_analysis(model_id="m1", num_modes=3)
        factors = [m.critical_load_factor for m in task.buckling_modes]
        assert factors == sorted(factors)


class TestFEniCSAdvancedService:
    def setup_method(self):
        self.service = FEniCSAdvancedService()

    def test_submit_custom_fea(self):
        task = self.service.submit_custom_fea(
            model_id="m1", project_id="p1", tenant_id="t1",
            ufl_filename="elasticity.ufl",
            ufl_content="a = Coefficient(G)"
        )
        assert task.status == CustomFEAStatus.COMPLETED
        assert len(task.solution_fields) >= 1

    def test_extract_peaks(self):
        data = [0, 10, 5, 15, 3, 8, 0]
        peaks = self.service._extract_peaks(data)
        assert len(peaks) >= 3