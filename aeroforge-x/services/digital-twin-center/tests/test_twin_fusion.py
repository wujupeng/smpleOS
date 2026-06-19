from __future__ import annotations

import pytest

from src.domain.entities.unified_twin import (
    ConflictResolution,
    CrossTwinInsight,
    FusionRecord,
    FusionStatus,
    InsightCategory,
    InsightSeverity,
    TwinDataConflict,
    TwinReference,
    UnifiedTwin,
)
from src.domain.services.twin_fusion_domain_service import TwinFusionDomainService
from src.domain.services.twin_loop_service import TwinLoopService
from src.domain.services.reduced_order_model_service import (
    FidelityLevel,
    MultiFidelityService,
    ReducedOrderModelService,
)


class TestUnifiedTwinEntity:
    def test_create_unified_twin(self):
        twin = UnifiedTwin("AF-X100-SN001", "t1", "p1")
        assert twin.aircraft_serial_number == "AF-X100-SN001"
        assert twin.fusion_status == FusionStatus.NOT_FUSED

    def test_set_twin_reference(self):
        twin = UnifiedTwin("AF-X100-SN001", "t1", "p1")
        twin.set_twin_reference("design", TwinReference(twin_id="dt-1", twin_type="design"))
        assert twin.design_twin_ref is not None
        assert twin.design_twin_ref.twin_id == "dt-1"

    def test_update_fusion_status(self):
        twin = UnifiedTwin("AF-X100-SN001", "t1", "p1")
        twin.set_twin_reference("design", TwinReference(twin_id="dt-1", twin_type="design"))
        twin.update_fusion_status()
        assert twin.fusion_status == FusionStatus.PARTIAL_FUSION

    def test_full_fusion_status(self):
        twin = UnifiedTwin("AF-X100-SN001", "t1", "p1")
        twin.set_twin_reference("design", TwinReference(twin_id="dt-1", twin_type="design"))
        twin.set_twin_reference("manufacturing", TwinReference(twin_id="mt-1", twin_type="manufacturing"))
        twin.set_twin_reference("flight", TwinReference(twin_id="ft-1", twin_type="flight"))
        twin.set_twin_reference("maintenance", TwinReference(twin_id="mt2-1", twin_type="maintenance"))
        twin.update_fusion_status()
        assert twin.fusion_status == FusionStatus.FULL_FUSION

    def test_add_insight_and_conflict(self):
        twin = UnifiedTwin("AF-X100-SN001", "t1", "p1")
        insight = CrossTwinInsight(
            insight_id="INS-001", category=InsightCategory.DESIGN_DEVIATION,
            severity=InsightSeverity.WARNING, source_twin="manufacturing", target_twin="design",
            description="Test insight",
        )
        twin.add_insight(insight)
        assert len(twin.cross_twin_insights) == 1

        conflict = TwinDataConflict(conflict_id="CF-001", parameter="thickness")
        twin.add_conflict(conflict)
        assert len(twin.conflicts) == 1


class TestTwinFusionDomainService:
    def setup_method(self):
        self.service = TwinFusionDomainService()

    def test_create_unified_twin(self):
        twin = self.service.create_unified_twin(
            "AF-X100-SN001", "t1", "p1",
            design_twin_id="dt-1", flight_twin_id="ft-1",
        )
        assert twin.fusion_status == FusionStatus.PARTIAL_FUSION
        assert twin.get_active_twin_count() == 2

    def test_fuse_twin_data(self):
        self.service.create_unified_twin("AF-X100-SN001", "t1", "p1")
        result = self.service.fuse_twin_data(
            "AF-X100-SN001",
            design_data={"parameters": {"thickness": 5.0}},
            manufacturing_data={"deviations": {"thickness": 5.3}},
            flight_data={"loads": {"max_load_factor": 3.5}, "measurements": {"thickness": 5.4}},
            maintenance_data={"health_indicators": {"degradation_rate": 0.04}},
        )
        assert result["fusion_version"] == 1
        assert result["insights_generated"] > 0

    def test_detect_cross_twin_anomaly(self):
        self.service.create_unified_twin("AF-X100-SN001", "t1", "p1")
        self.service.fuse_twin_data(
            "AF-X100-SN001",
            design_data={"parameters": {"thickness": 5.0}},
            manufacturing_data={"deviations": {"thickness": 5.3}},
            flight_data={"loads": {"max_load_factor": 3.5}},
            maintenance_data={"health_indicators": {"degradation_rate": 0.06}},
        )
        anomalies = self.service.detect_cross_twin_anomaly("AF-X100-SN001")
        assert isinstance(anomalies, list)

    def test_reconcile_conflicts(self):
        self.service.create_unified_twin("AF-X100-SN001", "t1", "p1")
        self.service.fuse_twin_data(
            "AF-X100-SN001",
            design_data={"parameters": {"thickness": 5.0}},
            flight_data={"measurements": {"thickness": 5.8}},
        )
        twin = self.service.get_unified_twin("AF-X100-SN001")
        if twin and twin.conflicts:
            conflict_id = twin.conflicts[0].conflict_id
            result = self.service.reconcile_conflicts(
                "AF-X100-SN001", conflict_id, ConflictResolution.DESIGN_WINS, "admin",
            )
            assert result["resolved"] is True


class TestTwinLoopService:
    def setup_method(self):
        self.service = TwinLoopService()

    def test_flight_to_design_feedback(self):
        feedbacks = self.service.feedback_flight_to_design(
            "AF-X100-SN001",
            flight_data={"loads": {"max_load_factor": 3.9}, "performance": {"cruise_drag_count": 210}},
            design_data={"limits": {"limit_load_factor": 3.8}, "targets": {"cruise_drag_count": 200}},
        )
        assert len(feedbacks) >= 1
        assert feedbacks[0].source_domain == "flight"
        assert feedbacks[0].target_domain == "design"

    def test_mfg_to_design_feedback(self):
        feedbacks = self.service.feedback_manufacturing_to_design(
            "AF-X100-SN001",
            manufacturing_data={"deviations": {"thickness": 0.12}, "assembly_issues": [{"description": "Tight clearance"}]},
            design_data={"tolerances": {"thickness": 0.1}},
        )
        assert len(feedbacks) >= 1

    def test_flight_to_maint_feedback(self):
        feedbacks = self.service.feedback_flight_to_maintenance(
            "AF-X100-SN001",
            flight_data={"load_trend": {"avg_load_factor": 3.0}},
            maintenance_data={"health_indicators": {"degradation_rate": 0.05}, "inspection_interval_hours": 500},
        )
        assert len(feedbacks) >= 1

    def test_maint_to_mfg_feedback(self):
        feedbacks = self.service.feedback_maintenance_to_manufacturing(
            "AF-X100-SN001",
            maintenance_data={"repair_history": [{"part_number": "P001"}, {"part_number": "P001"}, {"part_number": "P001"}], "part_lifetimes": {"P002": 3000}},
            manufacturing_data={"design_lifetimes": {"P002": 5000}},
        )
        assert len(feedbacks) >= 1

    def test_generate_loop_report(self):
        self.service.feedback_flight_to_design("SN001", {"loads": {"max_load_factor": 4.0}}, {"limits": {"limit_load_factor": 3.8}})
        report = self.service.generate_loop_report("SN001")
        assert report.total_feedbacks >= 1
        assert report.report_id is not None


class TestReducedOrderModelService:
    def setup_method(self):
        self.service = ReducedOrderModelService()

    def test_build_rom(self):
        hf_results = [
            {"field_data": [1.0, 2.0, 3.0, 4.0, 5.0]},
            {"field_data": [1.1, 2.1, 3.1, 4.1, 5.1]},
            {"field_data": [0.9, 1.9, 2.9, 3.9, 4.9]},
        ]
        model = self.service.build_reduced_order_model("aerodynamic", hf_results, basis_dimension=3)
        assert model.model_id is not None
        assert model.training_samples == 3
        assert model.accuracy_percent > 0

    def test_run_rom_simulation(self):
        hf_results = [{"field_data": [1.0, 2.0, 3.0]}]
        model = self.service.build_reduced_order_model("aerodynamic", hf_results)
        result = self.service.run_reduced_simulation(model.model_id, {"scale_factor": 1.5})
        assert result.fidelity_level == "rom"
        assert result.outputs is not None
        assert result.execution_time_ms < 100

    def test_update_rom(self):
        hf_results = [{"field_data": [1.0, 2.0, 3.0]}]
        model = self.service.build_reduced_order_model("structural", hf_results)
        updated = self.service.update_rom_from_high_fidelity(model.model_id, [{"field_data": [1.2, 2.2, 3.2]}])
        assert updated.version == 2
        assert updated.training_samples == 2

    def test_structural_rom(self):
        model = self.service.build_reduced_order_model("structural", [{"field_data": [1.0, 2.0]}])
        result = self.service.run_reduced_simulation(model.model_id, {"scale_factor": 2.0})
        assert "max_stress_mpa" in result.outputs
        assert "safety_factor" in result.outputs

    def test_thermal_rom(self):
        model = self.service.build_reduced_order_model("thermal", [{"field_data": [1.0, 2.0]}])
        result = self.service.run_reduced_simulation(model.model_id, {"scale_factor": 1.0})
        assert "max_temperature_c" in result.outputs


class TestMultiFidelityService:
    def setup_method(self):
        self.service = MultiFidelityService()

    def test_select_fidelity_rom(self):
        result = self.service.select_fidelity_level("aerodynamic", required_accuracy=90.0, max_time_seconds=0.5)
        assert result["recommended_level"] == "rom"

    def test_select_fidelity_high(self):
        result = self.service.select_fidelity_level("structural", required_accuracy=99.0, max_time_seconds=3600.0)
        assert result["recommended_level"] == "high"

    def test_run_rom_fidelity(self):
        model = self.service.build_rom("aerodynamic", [{"field_data": [1.0, 2.0]}])
        result = self.service.run_multi_fidelity_simulation(model.model_id, {"scale_factor": 1.0}, "rom")
        assert result.fidelity_level == "rom"

    def test_run_medium_fidelity(self):
        result = self.service.run_multi_fidelity_simulation(None, {"scale_factor": 1.0}, "medium")
        assert result.fidelity_level == "medium"

    def test_run_high_fidelity(self):
        result = self.service.run_multi_fidelity_simulation(None, {"scale_factor": 1.0}, "high")
        assert result.fidelity_level == "high"