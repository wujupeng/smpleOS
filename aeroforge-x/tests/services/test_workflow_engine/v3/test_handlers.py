import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "services", "workflow-engine-service"))

from src.domain.handlers.activity_handler_v3 import HandlerInput, HandlerOutput
from src.domain.handlers.v3_handlers import (
    DesignRuleCheckHandler, CAETriggerHandler, CFDAnalysisHandler, FEAAnalysisHandler,
    MBOMTransformHandler, WorkOrderGenerateHandler, ComplianceCheckHandler,
    ComplianceImpactHandler, FRACASCreateHandler, RootCauseAnalysisHandler, InspectionHandler,
)
from src.domain.services.propagation_chain_service import PropagationChainService


class TestDesignRuleCheckHandler:
    def setup_method(self):
        self.handler = DesignRuleCheckHandler()

    def test_no_violations(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001", rule_set_id="rules-v1",
            parameters={"geometry": {"wingspan": 10, "aspect_ratio": 8, "taper_ratio": 0.4, "wing_area": 16}, "structure": {"yield_strength": 500, "design_weight": 500, "skin_thickness": 3}},
        ))
        assert result.status == "completed"
        violations = result.result.get("violations", [])
        assert all(v["severity"] != "error" for v in violations) or len(violations) == 0

    def test_high_aspect_ratio_warning(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001", rule_set_id="rules-v1",
            parameters={"geometry": {"wingspan": 30, "aspect_ratio": 25, "taper_ratio": 0.4, "wing_area": 16}, "structure": {"yield_strength": 500, "design_weight": 500}},
        ))
        violations = result.result["violations"]
        assert any(v["rule"] == "AR-001" for v in violations)

    def test_low_taper_ratio_error(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001", rule_set_id="rules-v1",
            parameters={"geometry": {"wingspan": 10, "aspect_ratio": 8, "taper_ratio": 0.1, "wing_area": 16}, "structure": {"yield_strength": 500, "design_weight": 500}},
        ))
        violations = result.result["violations"]
        assert any(v["rule"] == "TR-001" for v in violations)

    def test_stress_exceeds_yield(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001", rule_set_id="rules-v1",
            parameters={"geometry": {"wingspan": 10, "aspect_ratio": 8, "taper_ratio": 0.4, "wing_area": 0.1}, "structure": {"yield_strength": 10, "design_weight": 50000, "skin_thickness": 0.001}},
        ))
        violations = result.result["violations"]
        assert any(v["rule"] == "STR-001" for v in violations)

    def test_validate_input_missing_model_id(self):
        errors = self.handler.validate_input(HandlerInput(rule_set_id="r1"))
        assert len(errors) > 0

    def test_schema_references(self):
        refs = self.handler.get_schema_references()
        assert "AircraftGeometry" in refs
        assert "AircraftStructure" in refs


class TestCAETriggerHandler:
    def setup_method(self):
        self.handler = CAETriggerHandler()

    def test_cae_params_extracted(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"geometry": {"wing_area": 120, "chord_length": 3.5, "wingspan": 35, "sweep_angle": 25}, "structure": {"material_id": "AL7075", "material_density": 2810, "yield_strength": 503, "elastic_modulus": 71.7}},
        ))
        assert result.status == "completed"
        cae_params = result.result["cae_input_parameters"]
        assert cae_params["reference_area"] == 120
        assert cae_params["reference_span"] == 35
        assert cae_params["material_id"] == "AL7075"


class TestCFDAnalysisHandler:
    def setup_method(self):
        self.handler = CFDAnalysisHandler()

    def test_cfd_results(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"geometry": {"wing_area": 16}, "envelope": {"V_s": 30, "V_C": 60, "V_D": 100, "h_max": 3000}},
        ))
        assert result.status == "completed"
        assert "scalar_results" in result.result
        assert "CL" in result.result["scalar_results"]
        assert "CD" in result.result["scalar_results"]


class TestFEAAnalysisHandler:
    def setup_method(self):
        self.handler = FEAAnalysisHandler()

    def test_fea_results(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"structure": {"yield_strength": 500}, "envelope": {"n_min": -1, "n_max": 3.5, "V_D": 100}},
        ))
        assert result.status == "completed"
        assert "scalar_results" in result.result
        assert result.result["scalar_results"]["safety_factor"] > 0


class TestMBOMTransformHandler:
    def setup_method(self):
        self.handler = MBOMTransformHandler()

    def test_ebom_to_mbom(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={
                "ebom_items": [
                    {"id": "wing-skin-001", "component_type": "wing_skin", "weight": 50, "material_id": "AL7075"},
                    {"id": "rib-001", "component_type": "rib", "weight": 5, "material_id": "AL7075"},
                    {"id": "unknown-part", "component_type": "custom", "weight": 10},
                ],
                "structure": {"design_weight": 500, "material_id": "AL7075"},
            },
        ))
        assert result.status == "completed"
        mbom = result.result["mbom_structure"]
        assert len(mbom) == 3
        assert mbom[0]["manufacturing_process"] == "CNC_milling"
        assert mbom[2]["status"] == "pending_confirmation"

    def test_unconfirmed_items(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"ebom_items": [{"id": "x", "component_type": "unknown_type"}], "structure": {}},
        ))
        assert len(result.result["unconfirmed_items"]) > 0


class TestWorkOrderGenerateHandler:
    def setup_method(self):
        self.handler = WorkOrderGenerateHandler()

    def test_work_orders_generated(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"mbom_items": [
                {"id": "wing-skin-001", "status": "mapped", "manufacturing_process": "CNC_milling", "material_id": "AL7075"},
                {"id": "rib-001", "status": "mapped", "manufacturing_process": "CNC_milling", "material_id": "AL7075"},
            ]},
        ))
        assert result.status == "completed"
        assert result.result["total_work_orders"] == 2
        assert result.result["work_orders"][0]["estimated_hours"] == 8.0

    def test_no_mapped_items(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"mbom_items": [{"id": "x", "status": "pending_confirmation"}]},
        ))
        assert result.result["total_work_orders"] == 0


class TestComplianceCheckHandler:
    def setup_method(self):
        self.handler = ComplianceCheckHandler()

    def test_compliant_with_evidence(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"certification": {"clause_number": "25.341", "compliance_status": "Compliant", "evidence_ref": "RPT-001"}},
        ))
        assert result.status == "completed"
        assert len(result.result["issues"]) == 0

    def test_compliant_without_evidence(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"certification": {"clause_number": "25.341", "compliance_status": "Compliant", "evidence_ref": ""}},
        ))
        assert len(result.result["issues"]) > 0

    def test_moc4_without_flight_test(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"certification": {"clause_number": "25.341", "compliance_method": "MOC4", "evidence_ref": "analysis_report"}},
        ))
        assert any("flight test" in i.lower() for i in result.result["issues"])


class TestComplianceImpactHandler:
    def setup_method(self):
        self.handler = ComplianceImpactHandler()

    def test_safety_keyword_triggers_review(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"anomaly_type": "structural_failure", "affected_components": ["wing_root"]},
        ))
        assert result.result["needs_review"] is True
        assert result.result["compliance_impact"] == "high"

    def test_non_safety_anomaly(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"anomaly_type": "cosmetic_defect", "affected_components": []},
        ))
        assert result.result["needs_review"] is False
        assert result.result["compliance_impact"] == "low"

    def test_battery_thermal_triggers_review(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"anomaly_type": "battery_thermal_runaway", "affected_components": ["battery_pack"]},
        ))
        assert result.result["needs_review"] is True


class TestFRACASCreateHandler:
    def setup_method(self):
        self.handler = FRACASCreateHandler()

    def test_create_fracas_report(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"anomaly_data": {
                "component_id": "battery-pack-001",
                "anomaly_type": "temperature_anomaly",
                "detected_values": {"temperature": 85},
                "predicted_values": {"temperature": 45},
                "deviation": 0.8,
                "timestamp": "2026-06-15T10:00:00Z",
            }},
        ))
        assert result.status == "completed"
        assert "FRACAS-" in result.result["fracas_report_id"]
        assert result.result["severity"] == "critical"

    def test_low_severity(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"anomaly_data": {"component_id": "sensor-001", "deviation": 0.1}},
        ))
        assert result.result["severity"] == "warning"


class TestRootCauseAnalysisHandler:
    def setup_method(self):
        self.handler = RootCauseAnalysisHandler()

    def test_temperature_anomaly_root_cause(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"fracas_report_id": "FRACAS-001", "anomaly_type": "temperature_anomaly"},
        ))
        assert result.result["root_cause"] == "cooling_system_degradation"
        assert result.result["confidence"] > 0

    def test_structural_anomaly_root_cause(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"fracas_report_id": "FRACAS-001", "anomaly_type": "structural_anomaly"},
        ))
        assert result.result["root_cause"] == "fatigue_crack_initiation"

    def test_battery_degradation_root_cause(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"fracas_report_id": "FRACAS-001", "anomaly_type": "battery_degradation"},
        ))
        assert result.result["root_cause"] == "calendar_aging_accelerated"

    def test_unknown_anomaly(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"fracas_report_id": "FRACAS-001", "anomaly_type": "unknown_type"},
        ))
        assert result.result["root_cause"] == "unknown"
        assert result.result["confidence"] == 0.0


class TestInspectionHandler:
    def setup_method(self):
        self.handler = InspectionHandler()

    def test_inspection_pass(self):
        result = self.handler.execute(HandlerInput(
            model_id="model-001",
            parameters={"work_order_id": "WO-001", "inspection_items": ["dimension_check", "surface_quality"]},
        ))
        assert result.status == "completed"
        assert result.result["inspection_result"] == "passed"
        assert result.result["items_checked"] == 2


class TestPropagationChainService:
    def setup_method(self):
        self.service = PropagationChainService()

    def test_list_chains(self):
        chains = self.service.list_chains()
        assert len(chains) >= 3

    def test_design_to_cae_chain(self):
        chains = self.service.list_chains()
        cae_chain = next((c for c in chains if c["name"] == "DesignToCAE"), None)
        assert cae_chain is not None
        assert len(cae_chain["handlers"]) >= 4

    def test_ebom_to_mbom_chain(self):
        chains = self.service.list_chains()
        mbom_chain = next((c for c in chains if c["name"] == "EBOMToMBOM"), None)
        assert mbom_chain is not None

    def test_twin_to_fracas_chain(self):
        chains = self.service.list_chains()
        fracas_chain = next((c for c in chains if c["name"] == "TwinToFRACAS"), None)
        assert fracas_chain is not None
        assert len(fracas_chain["gates"]) >= 2

    def test_execute_chain(self):
        chains = self.service.list_chains()
        chain = chains[0]
        result = self.service.execute_chain(chain["id"], {"model_id": "test-001"})
        assert result is not None