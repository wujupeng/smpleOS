import pytest

from services.design_center.src.domain.entities.aircraft_spec import AircraftSpec
from services.design_center.src.domain.services.model_domain_service import ParametricModelGenerator
from services.bom_center.src.domain.services.ebom_engine import EBOMEngine
from services.bom_center.src.domain.services.mbom_transform_domain_service import MBOMTransformDomainService
from services.bom_center.src.domain.services.sbom_gen_domain_service import SBOMGenerator
from services.bom_center.src.domain.services.bom_consistency_checker import BOMConsistencyChecker
from services.digital_twin_center.src.domain.services.twin_domain_service import TwinDomainService
from services.digital_twin_center.src.domain.services.design_twin_service import DesignTwinService
from services.digital_twin_center.src.domain.services.manufacturing_twin_service import ManufacturingTwinService
from services.digital_twin_center.src.domain.services.flight_twin_service import FlightTwinService
from services.digital_twin_center.src.domain.services.maintenance_twin_service import (
    MaintenanceTwinService, MaintenanceType, MaintenanceContent, MaintenanceResult,
)
from services.digital_twin_center.src.domain.services.twin_loop_service import TwinLoopService
from services.plm_center.src.domain.services.change_mgmt_domain_service import ChangeMgmtDomainService
from services.plm_center.src.domain.services.baseline_domain_service import BaselineDomainService
from services.plm_center.src.domain.services.impact_analysis_service import ImpactAnalysisService
from services.mes_center.src.domain.services.process_route_domain_service import ProcessRouteDomainService
from services.cae_center.src.domain.services.cfd.cfd_domain_service import CFDDomainService
from services.cae_center.src.domain.services.fea.fea_domain_service import FEADomainService
from services.cae_center.src.domain.services.flutter.flutter_domain_service import FlutterDomainService
from services.cae_center.src.domain.services.thermal.thermal_domain_service import ThermalDomainService
from services.security_audit.src.security_audit_service import SecurityAuditService


def _make_spec_and_ebom():
    spec = AircraftSpec(
        aircraft_type="fixed_wing",
        payload_kg=120,
        range_km=200,
        cruise_speed_kmh=120,
        takeoff_distance_m=80,
        power_type="electric",
        created_by="uat-tester",
    )
    model_gen = ParametricModelGenerator()
    model = model_gen.generate({
        "aircraft_type": spec.aircraft_type,
        "payload_kg": spec.payload_kg,
        "range_km": spec.range_km,
        "cruise_speed_kmh": spec.cruise_speed_kmh,
        "template": {
            "default_params": {
                "aspect_ratio": 8.0,
                "wing_sweep_deg": 5.0,
                "taper_ratio": 0.6,
            },
        },
    })
    ebom_engine = EBOMEngine()
    ebom = ebom_engine.generate_from_model(spec_id=spec.id, model_data=model)
    ebom.publish()
    return spec, ebom


class TestUATP2_Scenario1_CAEAnalysisWorkflow:
    def test_cfd_analysis_full_lifecycle(self) -> None:
        service = CFDDomainService()
        task = service.create_cfd_task(
            aircraft_id="UAT-AC-001",
            analysis_type="external_aerodynamics",
            mesh_task_id="mesh-uat-001",
            boundary_conditions={"mach": 0.25, "aoa": 3.0, "altitude": 2000},
        )
        assert task.status.value == "pending"

        service.submit_task(task)
        assert task.status.value == "running"

        service.complete_task(task, results={
            "lift_coefficient": 0.82,
            "drag_coefficient": 0.022,
        })
        assert task.status.value == "completed"

    def test_fea_analysis_full_lifecycle(self) -> None:
        service = FEADomainService()
        task = service.create_fea_task(
            aircraft_id="UAT-AC-001",
            analysis_type="static_strength",
            mesh_task_id="mesh-uat-002",
            load_conditions={"max_load": 50000},
        )
        service.submit_task(task)
        service.complete_task(task, results={
            "max_stress_mpa": 320.0,
            "safety_factor": 1.9,
        })
        assert task.status.value == "completed"

    def test_flutter_analysis(self) -> None:
        service = FlutterDomainService()
        task = service.create_flutter_task(
            aircraft_id="UAT-AC-001",
            analysis_type="flutter_analysis",
            mesh_task_id="mesh-uat-003",
            flight_conditions={"altitude": 3000, "mach": 0.3, "speed_range": [50, 150]},
        )
        assert task is not None

    def test_thermal_analysis(self) -> None:
        service = ThermalDomainService()
        task = service.create_thermal_task(
            aircraft_id="UAT-AC-001",
            analysis_type="steady_state",
            mesh_task_id="mesh-uat-004",
            thermal_conditions={"ambient_temp": -40, "internal_temp": 25, "heat_sources": ["engine"]},
        )
        assert task is not None


class TestUATP2_Scenario2_DigitalTwinLifecycle:
    def test_design_twin_sync_and_snapshot(self) -> None:
        twin_service = TwinDomainService()
        design_service = DesignTwinService(twin_service)

        twin = design_service.sync_with_design(
            "UAT-AC-002",
            {"wing_span": 15.0, "fuselage_length": 20.0},
            "designer-1",
            "initial_design",
        )
        assert twin is not None

        snapshot = design_service.get_design_snapshot("UAT-AC-002")
        assert snapshot is not None
        assert snapshot["aircraft_sn"] == "UAT-AC-002"

    def test_manufacturing_twin_with_deviation_detection(self) -> None:
        twin_service = TwinDomainService()
        mfg_service = ManufacturingTwinService(twin_service)

        twin = mfg_service.sync_with_measurement(
            "UAT-AC-003",
            measurement_data={"wing_span": 15.05, "fuselage_length": 20.02},
            design_data={"wing_span": 15.0, "fuselage_length": 20.0},
            tolerances={"wing_span": 0.03, "fuselage_length": 0.05},
        )
        assert twin is not None

        stats = mfg_service.get_deviation_statistics("UAT-AC-003")
        assert "total_dimensions" in stats

    def test_flight_twin_telemetry_and_health(self) -> None:
        twin_service = TwinDomainService()
        flight_service = FlightTwinService(twin_service)

        flight_service.ingest_telemetry("UAT-AC-004", [
            {"metric_name": "wing_lift", "metric_value": 45000.0},
            {"metric_name": "engine_thrust", "metric_value": 22000.0},
        ])

        assessments = flight_service.assess_structural_health(
            "UAT-AC-004",
            component_loads={"wing_lift": 45000.0, "engine_thrust": 22000.0},
            flight_hours=3000.0,
        )
        assert len(assessments) > 0

        for a in assessments:
            assert a.health_status.value in ("normal", "warning", "critical")
            assert a.load_ratio > 0

    def test_maintenance_twin_record_and_plan(self) -> None:
        twin_service = TwinDomainService()
        maintenance_service = MaintenanceTwinService(twin_service)

        record = maintenance_service.record_maintenance(
            "UAT-AC-005",
            maintenance_type=MaintenanceType.PREVENTIVE,
            content=MaintenanceContent.INSPECTION,
            result=MaintenanceResult.COMPLETED,
            component_id="landing_gear",
            component_name="Landing Gear",
            performed_by="tech-uat",
            flight_hours=8000.0,
        )
        assert record.record_id.startswith("MR-")

        estimates = maintenance_service.estimate_remaining_life("UAT-AC-005", flight_hours=8000.0)
        assert len(estimates) > 0

        plan = maintenance_service.generate_maintenance_plan("UAT-AC-005", flight_hours=8000.0)
        assert len(plan) > 0


class TestUATP2_Scenario3_TwinClosedLoop:
    def test_manufacturing_to_design_feedback(self) -> None:
        twin_service = TwinDomainService()
        design_service = DesignTwinService(twin_service)
        mfg_service = ManufacturingTwinService(twin_service)
        loop_service = TwinLoopService(twin_service, design_service, mfg_service)

        design_service.sync_with_design("UAT-LOOP-001", {"wing_span": 15.0}, "eng", "init")
        mfg_service.sync_with_measurement(
            "UAT-LOOP-001",
            measurement_data={"wing_span": 15.06},
            design_data={"wing_span": 15.0},
            tolerances={"wing_span": 0.03},
        )

        record = loop_service.feedback_to_design("UAT-LOOP-001", source_type="manufacturing")
        assert record is not None

    def test_conflict_detection_and_resolution(self) -> None:
        twin_service = TwinDomainService()
        design_service = DesignTwinService(twin_service)
        mfg_service = ManufacturingTwinService(twin_service)
        loop_service = TwinLoopService(twin_service, design_service, mfg_service)

        design_service.sync_with_design("UAT-CONFLICT-001", {"wing_span": 15.0}, "eng", "init")
        mfg_service.sync_with_measurement(
            "UAT-CONFLICT-001",
            measurement_data={"wing_span": 15.0},
            design_data={"wing_span": 15.0},
        )

        conflicts = loop_service.detect_conflict(
            "UAT-CONFLICT-001",
            manufacturing_data={"wing_span": 15.0},
            flight_data={"wing_span": 15.1},
            conflict_threshold=0.005,
        )
        assert len(conflicts) > 0

        resolved = loop_service.resolve_conflict(conflicts[0].conflict_id)
        assert resolved is not None
        assert resolved.resolved_at is not None


class TestUATP2_Scenario4_BOMFullPipeline:
    def test_ebom_to_mbom_to_sbom_pipeline(self) -> None:
        _, ebom = _make_spec_and_ebom()

        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform(ebom)
        assert mbom.root_item is not None

        sbom_gen = SBOMGenerator()
        sbom = sbom_gen.generate(ebom)
        assert sbom.root_item is not None

    def test_bom_consistency_validation(self) -> None:
        _, ebom = _make_spec_and_ebom()
        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform(ebom)

        checker = BOMConsistencyChecker()
        result = checker.check_consistency(ebom, mbom)
        assert "is_consistent" in result


class TestUATP2_Scenario5_ChangeManagementFullFlow:
    def test_ecr_to_ecn_lifecycle(self) -> None:
        service = ChangeMgmtDomainService()

        ecr = service.submit_ecr(
            title="UAT: 机翼材料替换",
            description="碳纤维替换铝合金",
            submitter="uat-designer",
            change_type="material",
            affected_items=["wing-001"],
        )
        assert ecr.status == "submitted"

        ecr = service.approve_ecr(ecr.ecr_id, "uat-chief", "批准")
        assert ecr.status == "approved"

        eco = service.create_eco(ecr_id=ecr.ecr_id, title="UAT: 实施", implementer="uat-mfg")
        eco = service.approve_eco(eco.eco_id, "uat-chief", "批准")
        eco = service.implement_eco(eco.eco_id)
        assert eco.status == "implemented"

        ecn = service.release_ecn(eco.eco_id, "uat-quality")
        assert ecn.status == "released"

    def test_baseline_freeze_unfreeze(self) -> None:
        service = BaselineDomainService()
        baseline = service.establish_baseline(
            name="UAT-BL-001",
            description="UAT测试基线",
            object_ids=["wing-001", "fuse-001"],
            established_by="uat-chief",
        )
        assert baseline.status == "active"

        service.freeze_baseline(baseline.baseline_id)
        assert baseline.status == "frozen"

        service.unfreeze_baseline(baseline.baseline_id, "uat-chief", "UAT需要更新")
        assert baseline.status == "active"

    def test_impact_analysis_for_change(self) -> None:
        service = ImpactAnalysisService()
        result = service.analyze_impact(
            change_description="UAT: 机翼材料替换",
            affected_items=["wing-001"],
        )
        assert "affected_parts" in result
        assert "safety_critical" in result


class TestUATP2_Scenario6_ProcessRouteGeneration:
    def test_auto_generate_process_routes(self) -> None:
        _, ebom = _make_spec_and_ebom()
        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform(ebom)

        route_service = ProcessRouteDomainService()
        routes = route_service.generate_routes(mbom)
        assert len(routes) > 0

        for route in routes:
            assert route.part_id is not None
            assert len(route.operations) > 0
            has_qc = any("检验" in op.name or "QC" in op.name.upper() for op in route.operations)
            assert has_qc, f"Route for {route.part_id} missing QC step"


class TestUATP2_Scenario7_SecurityAuditCompliance:
    def test_full_security_audit(self) -> None:
        service = SecurityAuditService()
        result = service.run_full_audit()
        assert result["overall_passed"] is True
        assert result["overall_score"] >= 80

    def test_audit_detects_safety_critical_issues(self) -> None:
        service = SecurityAuditService()
        report = service.audit_change_management([
            {
                "title": "Wing spar change without proper approval",
                "status": "implemented",
                "approved_by": None,
                "affected_items": ["wing-spar-001"],
                "approvers": [],
            },
        ])
        assert report.passed is False
        assert len(report.findings) >= 2


class TestUATP2_Scenario8_CrossDomainEndToEnd:
    def test_design_to_manufacturing_full_journey(self) -> None:
        spec, ebom = _make_spec_and_ebom()

        twin_service = TwinDomainService()
        design_twin_service = DesignTwinService(twin_service)
        mfg_twin_service = ManufacturingTwinService(twin_service)

        design_twin = design_twin_service.sync_with_design(
            "UAT-E2E-001",
            {"wing_span": 15.0, "material": "aluminum"},
            "uat-chief",
            "initial_design",
        )
        assert design_twin is not None

        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform(ebom)

        mfg_twin = mfg_twin_service.sync_with_measurement(
            "UAT-E2E-001",
            measurement_data={"wing_span": 15.02},
            design_data={"wing_span": 15.0},
        )
        assert mfg_twin is not None

        route_service = ProcessRouteDomainService()
        routes = route_service.generate_routes(mbom)
        assert len(routes) > 0

        change_service = ChangeMgmtDomainService()
        ecr = change_service.submit_ecr(
            title="UAT-E2E: 材料优化",
            description="碳纤维替换",
            submitter="uat-eng",
            change_type="material",
            affected_items=["wing-001"],
        )
        ecr = change_service.approve_ecr(ecr.ecr_id, "uat-chief", "批准")
        assert ecr.status == "approved"

        design_twin_service.sync_with_design(
            "UAT-E2E-001",
            {"wing_span": 15.0, "material": "carbon_fiber"},
            "change-mgmt",
            "eco_implementation",
        )

        snapshot = design_twin_service.get_design_snapshot("UAT-E2E-001")
        assert snapshot is not None