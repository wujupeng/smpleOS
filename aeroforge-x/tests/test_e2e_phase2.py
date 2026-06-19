import pytest

from services.cae_center.src.domain.entities.mesh_task import MeshTask, MeshStatus
from services.cae_center.src.domain.entities.cfd_task import CFDTask, CFDStatus
from services.cae_center.src.domain.entities.fea_task import FEATask, FEAStatus
from services.cae_center.src.domain.services.cfd.cfd_domain_service import CFDDomainService
from services.cae_center.src.domain.services.fea.fea_domain_service import FEADomainService
from services.cae_center.src.domain.services.multiphysics.multiphysics_domain_service import MultiphysicsDomainService
from services.digital_twin_center.src.domain.entities.digital_twin import DigitalTwin, TwinType, SyncStatus
from services.digital_twin_center.src.domain.services.twin_domain_service import TwinDomainService
from services.digital_twin_center.src.domain.services.design_twin_service import DesignTwinService
from services.digital_twin_center.src.domain.services.manufacturing_twin_service import ManufacturingTwinService
from services.digital_twin_center.src.domain.services.flight_twin_service import FlightTwinService
from services.digital_twin_center.src.domain.services.maintenance_twin_service import (
    MaintenanceTwinService, MaintenanceType, MaintenanceContent, MaintenanceResult,
)
from services.digital_twin_center.src.domain.services.twin_loop_service import TwinLoopService
from services.bom_center.src.domain.entities.bom_item import EBOM
from services.bom_center.src.domain.services.ebom_engine import EBOMEngine
from services.bom_center.src.domain.services.mbom_transform_domain_service import MBOMTransformDomainService
from services.bom_center.src.domain.services.sbom_gen_domain_service import SBOMGenerator
from services.bom_center.src.domain.services.bom_consistency_checker import BOMConsistencyChecker
from services.plm_center.src.domain.services.baseline_domain_service import BaselineDomainService
from services.plm_center.src.domain.services.change_mgmt_domain_service import ChangeMgmtDomainService
from services.plm_center.src.domain.services.impact_analysis_service import ImpactAnalysisService
from services.mes_center.src.domain.services.process_route_domain_service import ProcessRouteDomainService


class TestE2ECAEToTwinFlow:
    def test_cfd_analysis_to_design_twin_feedback(self) -> None:
        cfd_service = CFDDomainService()
        task = cfd_service.create_cfd_task(
            aircraft_id="AC-001",
            analysis_type="external_aerodynamics",
            mesh_task_id="mesh-001",
            boundary_conditions={"mach": 0.3, "aoa": 2.0, "altitude": 3000},
        )
        assert task.status == CFDStatus.PENDING

        cfd_service.submit_task(task)
        assert task.status == CFDStatus.RUNNING

        cfd_service.complete_task(task, results={
            "lift_coefficient": 0.85,
            "drag_coefficient": 0.025,
            "pressure_distribution": {"max_cp": 1.2, "min_cp": -2.5},
        })
        assert task.status == CFDStatus.COMPLETED
        assert task.results["lift_coefficient"] == 0.85

        twin_service = TwinDomainService()
        design_twin_service = DesignTwinService(twin_service)

        twin = design_twin_service.sync_with_design(
            aircraft_sn="AC-001",
            design_params={
                "wing_span": 15.0,
                "cfd_lift_coeff": task.results["lift_coefficient"],
                "cfd_drag_coeff": task.results["drag_coefficient"],
            },
            changed_by="cae-engineer",
            reason="cfd_results_integration",
        )
        assert twin is not None
        assert twin.twin_type == TwinType.DESIGN
        assert twin.data_version == 1

    def test_fea_analysis_to_manufacturing_twin(self) -> None:
        fea_service = FEADomainService()
        task = fea_service.create_fea_task(
            aircraft_id="AC-001",
            analysis_type="static_strength",
            mesh_task_id="mesh-002",
            load_conditions={"max_load": 50000, "load_type": "bending"},
        )
        assert task.status == FEAStatus.PENDING

        fea_service.submit_task(task)
        fea_service.complete_task(task, results={
            "max_stress_mpa": 350.0,
            "safety_factor": 1.8,
            "displacement_mm": 2.5,
        })
        assert task.status == FEAStatus.COMPLETED

        twin_service = TwinDomainService()
        mfg_twin_service = ManufacturingTwinService(twin_service)

        twin = mfg_twin_service.sync_with_measurement(
            aircraft_sn="AC-001",
            measurement_data={
                "wing_bending_stiffness": 350.0,
                "wing_displacement": 2.5,
            },
            design_data={
                "wing_bending_stiffness": 380.0,
                "wing_displacement": 2.0,
            },
            tolerances={
                "wing_bending_stiffness": 50.0,
                "wing_displacement": 0.5,
            },
        )
        assert twin is not None
        assert twin.twin_type == TwinType.MANUFACTURING


class TestE2ETwinClosedLoop:
    def test_manufacturing_feedback_to_design(self) -> None:
        twin_service = TwinDomainService()
        design_service = DesignTwinService(twin_service)
        mfg_service = ManufacturingTwinService(twin_service)
        loop_service = TwinLoopService(twin_service, design_service, mfg_service)

        design_service.sync_with_design("AC-002", {"wing_span": 15.0}, "engineer-1", "initial")
        mfg_service.sync_with_measurement(
            "AC-002",
            measurement_data={"wing_span": 15.05},
            design_data={"wing_span": 15.0},
            tolerances={"wing_span": 0.03},
        )

        record = loop_service.feedback_to_design("AC-002", source_type="manufacturing")
        assert record is not None
        assert record.feedback_type == "manufacturing_to_design"

    def test_flight_twin_to_maintenance_plan(self) -> None:
        twin_service = TwinDomainService()
        flight_service = FlightTwinService(twin_service)
        maintenance_service = MaintenanceTwinService(twin_service)

        flight_service.ingest_telemetry("AC-003", [
            {"metric_name": "wing_lift", "metric_value": 45000.0},
            {"metric_name": "engine_thrust", "metric_value": 22000.0},
        ])

        assessments = flight_service.assess_structural_health(
            "AC-003",
            component_loads={"wing_lift": 45000.0, "engine_thrust": 22000.0},
            flight_hours=5000.0,
        )
        assert len(assessments) > 0

        anomalies = flight_service.detect_anomaly("AC-003", {
            "temperature_engine": 120.0,
            "vibration_wing": 2500.0,
        })
        assert len(anomalies) > 0

        maintenance_service.record_maintenance(
            "AC-003",
            maintenance_type=MaintenanceType.PREVENTIVE,
            content=MaintenanceContent.INSPECTION,
            result=MaintenanceResult.COMPLETED,
            component_id="wing",
            component_name="Wing Assembly",
            performed_by="tech-1",
            flight_hours=5000.0,
        )

        estimates = maintenance_service.estimate_remaining_life("AC-003", flight_hours=5000.0)
        assert len(estimates) > 0

        plan = maintenance_service.generate_maintenance_plan(
            "AC-003",
            flight_hours=5000.0,
            health_assessments=[a.to_dict() for a in assessments],
            anomalies=[a.to_dict() for a in anomalies],
        )
        assert len(plan) > 0

    def test_conflict_detection_manufacturing_vs_flight(self) -> None:
        twin_service = TwinDomainService()
        design_service = DesignTwinService(twin_service)
        mfg_service = ManufacturingTwinService(twin_service)
        loop_service = TwinLoopService(twin_service, design_service, mfg_service)

        design_service.sync_with_design("AC-004", {"wing_span": 15.0}, "eng", "init")
        mfg_service.sync_with_measurement(
            "AC-004",
            measurement_data={"wing_span": 15.0},
            design_data={"wing_span": 15.0},
        )

        conflicts = loop_service.detect_conflict(
            "AC-004",
            manufacturing_data={"wing_span": 15.0},
            flight_data={"wing_span": 15.08},
            conflict_threshold=0.005,
        )
        assert len(conflicts) > 0
        assert conflicts[0].resolution.value == "manufacturing_wins"


class TestE2EBOMFullPipeline:
    def test_ebom_to_mbom_to_sbom(self) -> None:
        from services.design_center.src.domain.entities.aircraft_spec import AircraftSpec
        from services.design_center.src.domain.services.spec_domain_service import SpecDomainService
        from services.design_center.src.domain.services.model_domain_service import ParametricModelGenerator

        spec = AircraftSpec(
            aircraft_type="fixed_wing",
            payload_kg=120,
            range_km=200,
            cruise_speed_kmh=120,
            takeoff_distance_m=80,
            power_type="electric",
            created_by="chief-1",
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
        assert ebom.root_item is not None
        ebom.publish()

        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform(ebom)
        assert mbom is not None
        assert mbom.root_item is not None

        sbom_gen = SBOMGenerator()
        sbom = sbom_gen.generate(ebom)
        assert sbom is not None
        assert sbom.root_item is not None

    def test_bom_consistency_check(self) -> None:
        from services.design_center.src.domain.entities.aircraft_spec import AircraftSpec
        from services.design_center.src.domain.services.model_domain_service import ParametricModelGenerator

        spec = AircraftSpec(
            aircraft_type="fixed_wing",
            payload_kg=120,
            range_km=200,
            cruise_speed_kmh=120,
            takeoff_distance_m=80,
            power_type="electric",
            created_by="chief-1",
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

        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform(ebom)

        checker = BOMConsistencyChecker()
        result = checker.check_consistency(ebom, mbom)
        assert "is_consistent" in result
        assert "differences" in result


class TestE2EChangeManagementFlow:
    def test_ecr_to_ecn_full_lifecycle(self) -> None:
        change_service = ChangeMgmtDomainService()

        ecr = change_service.submit_ecr(
            title="机翼材料替换",
            description="将铝合金替换为碳纤维复合材料以减重",
            submitter="design-eng-1",
            change_type="material",
            affected_items=["wing-001", "spar-001"],
        )
        assert ecr.status == "submitted"

        ecr = change_service.approve_ecr(ecr.ecr_id, "chief-eng", "批准材料替换")
        assert ecr.status == "approved"

        eco = change_service.create_eco(
            ecr_id=ecr.ecr_id,
            title="机翼碳纤维替换实施",
            implementer="mfg-eng-1",
            planned_changes={"wing-001": {"material": "carbon_fiber", "process": "autoclave"}},
        )
        assert eco.status == "draft"

        eco = change_service.approve_eco(eco.eco_id, "chief-eng", "批准实施")
        assert eco.status == "approved"

        eco = change_service.implement_eco(eco.eco_id)
        assert eco.status == "implemented"

        ecn = change_service.release_ecn(eco.eco_id, "quality-mgr")
        assert ecn.status == "released"

    def test_change_impact_analysis(self) -> None:
        impact_service = ImpactAnalysisService()

        result = impact_service.analyze_impact(
            change_description="机翼材料替换",
            affected_items=["wing-001", "spar-001"],
        )
        assert "affected_parts" in result
        assert "affected_bom_nodes" in result
        assert "safety_critical" in result

    def test_baseline_management(self) -> None:
        baseline_service = BaselineDomainService()

        baseline = baseline_service.establish_baseline(
            name="AAF-001-BL-001",
            description="初始设计基线",
            object_ids=["wing-001", "fuselage-001", "tail-001"],
            established_by="chief-eng",
        )
        assert baseline.status == "active"

        integrity = baseline_service.check_integrity(baseline.baseline_id)
        assert integrity["is_intact"] is True

        baseline_service.freeze_baseline(baseline.baseline_id)
        assert baseline.status == "frozen"

        baseline_service.unfreeze_baseline(baseline.baseline_id, "chief-eng", "需要更新")
        assert baseline.status == "active"


class TestE2EProcessRouteGeneration:
    def test_auto_generate_process_route(self) -> None:
        from services.design_center.src.domain.entities.aircraft_spec import AircraftSpec
        from services.design_center.src.domain.services.model_domain_service import ParametricModelGenerator

        spec = AircraftSpec(
            aircraft_type="fixed_wing",
            payload_kg=120,
            range_km=200,
            cruise_speed_kmh=120,
            takeoff_distance_m=80,
            power_type="electric",
            created_by="chief-1",
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

        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform(ebom)

        route_service = ProcessRouteDomainService()
        routes = route_service.generate_routes(mbom)
        assert len(routes) > 0

        for route in routes:
            assert route.part_id is not None
            assert len(route.operations) > 0
            has_qc = any("检验" in op.name or "QC" in op.name.upper() for op in route.operations)
            assert has_qc


class TestE2EMultiphysicsCoupling:
    def test_thermal_structural_coupling(self) -> None:
        multiphysics_service = MultiphysicsDomainService()

        task = multiphysics_service.create_coupled_analysis(
            aircraft_id="AC-001",
            analysis_types=["thermal", "structural"],
            coupling_config={
                "thermal_to_structural": True,
                "iteration_count": 3,
                "convergence_threshold": 0.01,
            },
        )
        assert task is not None

        result = multiphysics_service.run_coupled_analysis(task)
        assert "iterations" in result
        assert "converged" in result


class TestE2ECrossDomainIntegration:
    def test_design_change_propagates_through_all_systems(self) -> None:
        from services.design_center.src.domain.entities.aircraft_spec import AircraftSpec
        from services.design_center.src.domain.services.model_domain_service import ParametricModelGenerator

        spec = AircraftSpec(
            aircraft_type="fixed_wing",
            payload_kg=120,
            range_km=200,
            cruise_speed_kmh=120,
            takeoff_distance_m=80,
            power_type="electric",
            created_by="chief-1",
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

        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform(ebom)

        sbom_gen = SBOMGenerator()
        sbom = sbom_gen.generate(ebom)

        twin_service = TwinDomainService()
        design_twin_service = DesignTwinService(twin_service)
        design_twin = design_twin_service.sync_with_design(
            "AC-CROSS-001",
            design_params={"wing_span": 15.0, "material": "aluminum"},
            changed_by="chief-eng",
            reason="initial_design",
        )
        assert design_twin is not None

        change_service = ChangeMgmtDomainService()
        ecr = change_service.submit_ecr(
            title="机翼材料替换为碳纤维",
            description="减重优化",
            submitter="design-eng",
            change_type="material",
            affected_items=["wing-001"],
        )
        ecr = change_service.approve_ecr(ecr.ecr_id, "chief-eng", "批准")
        eco = change_service.create_eco(ecr_id=ecr.ecr_id, title="碳纤维替换实施", implementer="mfg-eng")
        eco = change_service.approve_eco(eco.eco_id, "chief-eng", "批准实施")
        eco = change_service.implement_eco(eco.eco_id)

        design_twin_service.sync_with_design(
            "AC-CROSS-001",
            design_params={"wing_span": 15.0, "material": "carbon_fiber"},
            changed_by="change-mgmt",
            reason="eco_implementation",
        )

        mfg_twin_service = ManufacturingTwinService(twin_service)
        mfg_twin = mfg_twin_service.sync_with_measurement(
            "AC-CROSS-001",
            measurement_data={"wing_span": 15.02, "material_composition": "carbon_fiber"},
            design_data={"wing_span": 15.0},
        )
        assert mfg_twin is not None

        route_service = ProcessRouteDomainService()
        routes = route_service.generate_routes(mbom)
        assert len(routes) > 0

        checker = BOMConsistencyChecker()
        consistency = checker.check_consistency(ebom, mbom)
        assert "is_consistent" in consistency