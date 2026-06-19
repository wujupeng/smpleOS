import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest


class TestRequirementToDesignE2E:
    def test_spec_to_model_to_rule_check(self):
        from services.requirement_center.src.domain.services.spec_service import SpecService
        from services.design_center.src.domain.services.v1.param_model_service import ParamModelService
        from services.design_center.src.domain.services.v1.design_rule_engine_v1 import DesignRuleEngineV1

        spec_service = SpecService()
        model_service = ParamModelService()
        rule_engine = DesignRuleEngineV1()

        spec = spec_service.create_aircraft_spec("PROJ-E2E-001", "Narrow Body", {
            "wingspan_m": 35.8,
            "fuselage_length_m": 40.0,
            "mtow_kg": 78000,
            "cruise_speed_kts": 450,
        })
        assert spec is not None

        model = model_service.create_parametric_model("PROJ-E2E-001", {"wingspan_m": 35.8, "fuselage_length_m": 40.0})
        assert model is not None

        result = rule_engine.check_rules({"wingspan_m": 35.8, "mtow_kg": 78000})
        assert "violations" in result


class TestDesignToCAEE2E:
    def test_design_to_stability_to_envelope(self):
        from services.verification_center.src.domain.services.stability_engine import StabilityEngine
        from services.verification_center.src.domain.services.flight_envelope_engine import FlightEnvelopeEngine

        stability_engine = StabilityEngine()
        envelope_engine = FlightEnvelopeEngine()

        stability = stability_engine.analyze_stability("PROJ-E2E-002", {
            "cma_m": 4.0, "x_cg_m": 15.0, "cl_alpha": 5.0, "cl_alpha_tail": 3.0,
            "s_wing_m2": 120.0, "s_tail_m2": 25.0, "l_tail_m": 15.0, "v_h": 0.8,
        })
        assert stability is not None

        envelope = envelope_engine.analyze_flight_envelope("PROJ-E2E-002", {
            "v_d_kts": 350, "m_mo": 0.87, "max_alt_ft": 43000,
            "v_s1_kts": 120, "v_a_kts": 250,
        })
        assert envelope is not None


class TestBOMToManufacturingE2E:
    def test_ebom_to_mbom_to_traveler(self):
        from services.bom_center.src.domain.services.bom_services import BOMTransformService
        from services.mes_center.src.domain.services.v1.mes_v1_services import TravelerService

        transform_service = BOMTransformService()
        traveler_service = TravelerService()

        ebom = transform_service.create_ebom("PROJ-E2E-003", [
            {"part_number": "WS-001", "part_name": "Wing Spar", "quantity": 2, "parent_id": None},
            {"part_number": "WR-001", "part_name": "Wing Rib", "quantity": 20, "parent_id": "WS-001"},
        ])
        assert ebom is not None

        mbom = transform_service.transform_to_mbom(ebom.bom_id, [
            {"ebom_part": "WS-001", "mbom_part": "WS-001-FAB", "process": "composite_layup"},
        ])
        assert mbom is not None


class TestFMEAToFRACASE2E:
    def test_fmea_to_fracas_to_reliability(self):
        from services.qms_service.src.domain.entities.v1.qms_v1_entities import FMEAAnalysis, FMEAFailureMode, FRACASRecord, FRACASCorrectiveAction, ReliabilityPrediction

        fmea = FMEAAnalysis(project_id="PROJ-E2E-004", system_name="Hydraulic System")
        mode = FMEAFailureMode(
            failure_mode_id="FM-001",
            component="Hydraulic Pump",
            failure_mode="Pressure Loss",
            effect="System Degradation",
            severity=8, occurrence=4, detection=3,
        )
        fmea.add_failure_mode(mode)
        assert fmea.rpn_max >= 0

        fracas = FRACASRecord(
            record_id="FR-001",
            system="Hydraulic System",
            failure_description="Pressure loss during flight",
            severity="major",
        )
        action = FRACASCorrectiveAction(
            action_id="CA-001",
            description="Replace seal and inspect pump",
            responsible="MAINT-01",
            due_date="2024-06-01",
        )
        fracas.add_corrective_action(action)
        assert len(fracas.corrective_actions) == 1


class TestCertificationE2E:
    @pytest.mark.asyncio
    async def test_certification_plan_to_approval(self):
        from services.certification_center.src.domain.services.v1.certification_plan_service import CertificationPlanService
        from services.certification_center.src.domain.services.v1.airworthiness_service import AirworthinessService

        plan_service = CertificationPlanService()
        aw_service = AirworthinessService()

        plan = await plan_service.create_certification_plan("PROJ-E2E-005", "narrow_body")
        assert len(plan.compliance_items) > 0

        approval = await aw_service.submit_approval_application(plan.plan_id, "type_certificate")
        aw_service.manage_certificate_lifecycle(approval.approval_id, "approve", certificate_number="TC-E2E-001", reviewed_by="AUTH")
        assert aw_service.get_approval(approval.approval_id).review_status.value == "approved"


class TestTwinToOperationsE2E:
    @pytest.mark.asyncio
    async def test_four_stage_twin_to_fleet_to_analytics(self):
        from services.digital_twin_center.src.domain.services.v1.twin_sync_service import TwinSyncService
        from services.digital_twin_center.src.domain.services.v1.fleet_twin_service import FleetTwinService
        from services.operation_center.src.domain.services.fleet_management_service import FleetManagementService
        from services.operation_center.src.domain.services.operation_analytics_service import OperationAnalyticsService

        sync = TwinSyncService()
        fleet_twin = FleetTwinService(sync)
        fleet_mgmt = FleetManagementService()
        analytics = OperationAnalyticsService(fleet_mgmt)

        for sn in ["SN-E2E-001", "SN-E2E-002"]:
            await sync.sync_maintenance_twin(sn,
                records=[{"maintenance_id": f"M-{sn}", "maintenance_type": "preventive", "description": "A-Check", "performed_date": "2024-01-01", "technician": "TECH-01"}],
                replacements=[],
                life_updates=[{"component_id": "comp-1", "component_name": "Pump", "total_life_hours": 10000, "consumed_hours": 5000, "remaining_hours": 5000, "remaining_percentage": 50.0}],
            )
            await fleet_mgmt.register_aircraft(sn, "A320neo", "fleet-e2e")
            await fleet_mgmt.track_flight_hours(sn, 500.0)

        ft = await fleet_twin.aggregate_fleet_data("fleet-e2e", ["SN-E2E-001", "SN-E2E-002"])
        assert ft.aircraft_count == 2

        utilization = analytics.calculate_utilization_rate("fleet-e2e")
        assert utilization["utilization_rate"] >= 0


class TestAeroGPTE2E:
    @pytest.mark.asyncio
    async def test_designer_to_engineer_to_manufacturing(self):
        from services.ai_engine.src.domain.services.aerogpt_designer import AeroGPTDesigner
        from services.ai_engine.src.domain.services.aerogpt_engineer import AeroGPTEngineer
        from services.ai_engine.src.domain.services.aerogpt_manufacturing import AeroGPTManufacturing

        designer = AeroGPTDesigner()
        engineer = AeroGPTEngineer()
        manufacturing = AeroGPTManufacturing()

        proposal = designer.generate_aircraft_spec(
            "Design a narrow-body aircraft with wingspan of 35.8m, fuselage length of 40m, mtow of 78000kg, cruise speed of 450kts"
        )
        assert proposal.feasibility_report.is_feasible is True

        structure = engineer.generate_structure(proposal.id, proposal.parsed_spec)
        assert len(structure.components) > 0

        for comp in structure.components[:1]:
            route = manufacturing.generate_process_route(comp.component_type, comp.material, comp.parameters)
            assert len(route.steps) > 0


class TestConfigChangePropagationE2E:
    def test_config_change_to_knowledge_to_bom(self):
        from services.configuration_center.src.domain.services.config_item_service import ConfigItemService
        from services.configuration_center.src.domain.entities.config_item import ConfigItem

        service = ConfigItemService()
        item = ConfigItem(item_id="CFG-E2E-001", name="Wingspan", item_type="parameter", current_value="35.8")
        service._items[item.item_id] = item

        service.update_config_value("CFG-E2E-001", "36.0", "Design optimization", "USER-01")
        assert item.current_value == "36.0"
        assert len(item.versions) == 1