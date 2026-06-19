import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "workflow-engine-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "physics-twin-service"))

from src.domain.handlers.activity_handler_v3 import HandlerInput
from src.domain.handlers.v3_handlers import (
    DesignRuleCheckHandler, CAETriggerHandler, CFDAnalysisHandler, FEAAnalysisHandler,
    MBOMTransformHandler, WorkOrderGenerateHandler,
    FRACASCreateHandler, RootCauseAnalysisHandler, ComplianceImpactHandler,
)
from src.domain.services.propagation_chain_service import PropagationChainService
from src.domain.services.domain_event_publisher import DomainEventPublisher, FieldChange


class TestDesignToCAEChain:
    def test_full_design_to_cae_propagation(self):
        geometry = {"wingspan": 35, "chord_length": 3.5, "sweep_angle": 25, "taper_ratio": 0.3, "wing_area": 120, "aspect_ratio": 10.2}
        structure = {"material_id": "AL7075", "material_density": 2810, "yield_strength": 503, "design_weight": 500, "skin_thickness": 3, "elastic_modulus": 71.7}
        envelope = {"V_s": 60, "V_A": 100, "V_C": 130, "V_D": 180, "h_max": 12000, "n_min": -1, "n_max": 3.5}

        rule_result = DesignRuleCheckHandler().execute(HandlerInput(
            model_id="wing-001", rule_set_id="rules-v1",
            parameters={"geometry": geometry, "structure": structure, "n_max": 3.5},
        ))
        assert rule_result.status == "completed"

        cae_result = CAETriggerHandler().execute(HandlerInput(
            model_id="wing-001",
            parameters={"geometry": geometry, "structure": structure},
        ))
        assert cae_result.status == "completed"
        assert "cae_input_parameters" in cae_result.result

        cfd_result = CFDAnalysisHandler().execute(HandlerInput(
            model_id="wing-001",
            parameters={"geometry": geometry, "envelope": envelope},
        ))
        assert cfd_result.status == "completed"
        assert "scalar_results" in cfd_result.result

        fea_result = FEAAnalysisHandler().execute(HandlerInput(
            model_id="wing-001",
            parameters={"structure": structure, "envelope": envelope},
        ))
        assert fea_result.status == "completed"
        assert fea_result.result["scalar_results"]["safety_factor"] > 0

    def test_design_change_triggers_event(self):
        event = DomainEventPublisher.publish_object_change_event(
            aggregate_id="wing-001",
            changed_fields=[FieldChange(field_path="wingspan", old_value=30.0, new_value=35.0, unit="m", schema_type="AircraftGeometry")],
        )
        assert event.event_type == "aeroforge.aircraft.object.updated"
        hints = DomainEventPublisher.build_propagation_hints(event.changed_fields)
        assert len(hints) > 0


class TestEBOMToMBOMChain:
    def test_full_ebom_to_mbom_propagation(self):
        ebom_items = [
            {"id": "wing-skin-001", "component_type": "wing_skin", "weight": 50, "material_id": "AL7075"},
            {"id": "rib-001", "component_type": "rib", "weight": 5, "material_id": "AL7075"},
            {"id": "spar-001", "component_type": "spar", "weight": 30, "material_id": "AL7075"},
            {"id": "fastener-001", "component_type": "fastener", "weight": 0.5, "material_id": "TI6AL4V"},
        ]
        structure = {"design_weight": 500, "material_id": "AL7075"}

        mbom_result = MBOMTransformHandler().execute(HandlerInput(
            model_id="bom-001",
            parameters={"ebom_items": ebom_items, "structure": structure},
        ))
        assert mbom_result.status == "completed"
        assert mbom_result.result["total_items"] == 4

        mapped_items = [item for item in mbom_result.result["mbom_structure"] if item["status"] == "mapped"]
        wo_result = WorkOrderGenerateHandler().execute(HandlerInput(
            model_id="bom-001",
            parameters={"mbom_items": mapped_items},
        ))
        assert wo_result.status == "completed"
        assert wo_result.result["total_work_orders"] > 0


class TestTwinToFRACASChain:
    def test_full_twin_to_fracas_propagation(self):
        anomaly_data = {
            "component_id": "battery-pack-001",
            "anomaly_type": "temperature_anomaly",
            "detected_values": {"temperature": 95},
            "predicted_values": {"temperature": 45},
            "deviation": 0.9,
            "timestamp": "2026-06-15T10:00:00Z",
        }

        fracas_result = FRACASCreateHandler().execute(HandlerInput(
            model_id="twin-001",
            parameters={"anomaly_data": anomaly_data},
        ))
        assert fracas_result.status == "completed"
        assert "FRACAS-" in fracas_result.result["fracas_report_id"]

        rca_result = RootCauseAnalysisHandler().execute(HandlerInput(
            model_id="twin-001",
            parameters={"fracas_report_id": fracas_result.result["fracas_report_id"], "anomaly_type": "temperature_anomaly"},
        ))
        assert rca_result.status == "completed"
        assert rca_result.result["root_cause"] == "cooling_system_degradation"

        impact_result = ComplianceImpactHandler().execute(HandlerInput(
            model_id="twin-001",
            parameters={"anomaly_type": "temperature_anomaly", "affected_components": ["battery_pack", "cooling_system"]},
        ))
        assert impact_result.status == "completed"
        assert impact_result.result["needs_review"] is True

    def test_safety_critical_dual_approval(self):
        impact_result = ComplianceImpactHandler().execute(HandlerInput(
            model_id="twin-001",
            parameters={"anomaly_type": "structural_failure", "affected_components": ["wing_root"]},
        ))
        assert impact_result.result["compliance_impact"] == "high"


class TestChainExecutionViaService:
    def setup_method(self):
        self.service = PropagationChainService()

    def test_design_to_cae_chain_execution(self):
        chains = self.service.list_chains()
        cae_chain = next((c for c in chains if c["name"] == "DesignToCAE"), None)
        assert cae_chain is not None
        result = self.service.execute_chain(cae_chain["id"], {
            "model_id": "wing-001",
            "parameters": {
                "geometry": {"wingspan": 35, "chord_length": 3.5, "wing_area": 120, "aspect_ratio": 10, "taper_ratio": 0.3},
                "structure": {"yield_strength": 503, "design_weight": 500, "skin_thickness": 3},
                "envelope": {"V_s": 60, "V_C": 130, "V_D": 180, "h_max": 12000, "n_max": 3.5},
            },
        })
        assert result is not None

    def test_ebom_to_mbom_chain_execution(self):
        chains = self.service.list_chains()
        mbom_chain = next((c for c in chains if c["name"] == "EBOMToMBOM"), None)
        assert mbom_chain is not None
        result = self.service.execute_chain(mbom_chain["id"], {
            "model_id": "bom-001",
            "parameters": {
                "ebom_items": [{"id": "wing-001", "component_type": "wing_skin", "weight": 50}],
                "structure": {"design_weight": 500},
            },
        })
        assert result is not None

    def test_twin_to_fracas_chain_execution(self):
        chains = self.service.list_chains()
        fracas_chain = next((c for c in chains if c["name"] == "TwinToFRACAS"), None)
        assert fracas_chain is not None
        result = self.service.execute_chain(fracas_chain["id"], {
            "model_id": "twin-001",
            "parameters": {
                "anomaly_data": {"component_id": "bat-001", "anomaly_type": "temperature_anomaly", "deviation": 0.8},
            },
        })
        assert result is not None