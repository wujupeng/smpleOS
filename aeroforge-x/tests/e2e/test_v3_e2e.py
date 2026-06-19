import pytest
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "physics-twin-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

from src.domain.schemas.aircraft_geometry import AircraftGeometry
from src.domain.schemas.aircraft_structure import AircraftStructure
from src.domain.schemas.aircraft_propulsion import AircraftPropulsion, TurbofanParams
from src.domain.schemas.aircraft_flight_envelope import AircraftFlightEnvelope
from src.domain.schemas.enums import EngineType
from src.domain.services.schema_migration_service import SchemaMigrationService
from src.domain.services.domain_event_publisher import DomainEventPublisher, FieldChange
from src.domain.plugins.dof6_model import DOF6Model
from src.domain.plugins.battery_model import BatteryModel
from src.domain.plugins.control_model import ControlModel
from src.domain.handlers.activity_handler_v3 import HandlerInput
from src.domain.handlers.v3_handlers import (
    DesignRuleCheckHandler, CAETriggerHandler, FRACASCreateHandler, RootCauseAnalysisHandler,
    MBOMTransformHandler, WorkOrderGenerateHandler,
)
from src.domain.services.propagation_chain_service import PropagationChainService


class TestE2ESchemaToCAEChain:
    def test_schema_definition_to_cae_results(self):
        geometry = AircraftGeometry(
            wingspan=35.0, chord_length=3.5, sweep_angle=25.0,
            taper_ratio=0.3, thickness_ratio=0.12, wing_area=120.0,
        )
        assert geometry.aspect_ratio == pytest.approx(35.0**2 / 120.0, rel=1e-3)

        structure = AircraftStructure(
            material_id="AL7075-T6", material_density=2810.0,
            yield_strength=503.0, ultimate_strength=572.0,
            elastic_modulus=71.7, design_weight=500.0,
            rib_spacing=0.5, skin_thickness=3.0,
        )
        assert structure.material_id == "AL7075-T6"

        event = DomainEventPublisher.publish_object_change_event(
            aggregate_id="wing-001",
            changed_fields=[FieldChange(field_path="wingspan", old_value=30.0, new_value=35.0, unit="m", schema_type="AircraftGeometry")],
        )
        assert event.event_type == "aeroforge.aircraft.object.updated"

        rule_result = DesignRuleCheckHandler().execute(HandlerInput(
            model_id="wing-001", rule_set_id="rules-v1",
            parameters={"geometry": geometry.model_dump(), "structure": structure.model_dump(), "n_max": 3.5},
        ))
        assert rule_result.status == "completed"

        cae_result = CAETriggerHandler().execute(HandlerInput(
            model_id="wing-001",
            parameters={"geometry": geometry.model_dump(), "structure": structure.model_dump()},
        ))
        assert cae_result.status == "completed"
        assert cae_result.result["cae_input_parameters"]["reference_area"] == 120.0


class TestE2ETwinToFRACASChain:
    def test_physics_model_to_fracas(self):
        dof6 = DOF6Model(fidelity="Mid")
        dof6.initialize({"mass": 1500.0, "Ixx": 1000.0, "Iyy": 3000.0, "Izz": 3500.0, "wing_area": 16.0, "wingspan": 10.0, "chord_length": 1.6, "initial_altitude": 1000.0, "initial_speed": 50.0})

        for _ in range(50):
            dof6.step(0.01)

        state = dof6.get_state()
        assert state["position"][0] > 0

        battery = BatteryModel(fidelity="Mid")
        battery.initialize({"capacity_Ah": 100.0, "R0": 0.01, "RC1": 0.005, "C1": 10000.0, "nominal_voltage": 400.0, "initial_soc": 1.0, "ocv_table": [(0.0, 300.0), (0.5, 380.0), (1.0, 420.0)]})

        for _ in range(20):
            battery.step(1.0, {"current": 50.0})

        battery_state = battery.get_state()
        assert battery_state["soc"] < 1.0

        anomaly_data = {
            "component_id": "battery-pack-001",
            "anomaly_type": "battery_degradation",
            "detected_values": {"soc": battery_state["soc"], "temperature": battery_state["temperature"]},
            "predicted_values": {"soc": 0.95},
            "deviation": abs(1.0 - battery_state["soc"]),
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
            parameters={"fracas_report_id": fracas_result.result["fracas_report_id"], "anomaly_type": "battery_degradation"},
        ))
        assert rca_result.result["root_cause"] == "calendar_aging_accelerated"


class TestE2EEBOMToMBOMChain:
    def test_ebom_generation_to_work_orders(self):
        ebom_items = [
            {"id": "wing-skin-001", "component_type": "wing_skin", "weight": 50, "material_id": "AL7075"},
            {"id": "rib-001", "component_type": "rib", "weight": 5, "material_id": "AL7075"},
            {"id": "spar-001", "component_type": "spar", "weight": 30, "material_id": "AL7075"},
        ]
        structure = AircraftStructure(
            material_id="AL7075-T6", material_density=2810.0,
            yield_strength=503.0, ultimate_strength=572.0,
            elastic_modulus=71.7, design_weight=500.0,
            rib_spacing=0.5, skin_thickness=3.0,
        )

        mbom_result = MBOMTransformHandler().execute(HandlerInput(
            model_id="bom-001",
            parameters={"ebom_items": ebom_items, "structure": structure.model_dump()},
        ))
        assert mbom_result.status == "completed"
        assert mbom_result.result["total_items"] == 3

        mapped_items = [item for item in mbom_result.result["mbom_structure"] if item["status"] == "mapped"]
        wo_result = WorkOrderGenerateHandler().execute(HandlerInput(
            model_id="bom-001",
            parameters={"mbom_items": mapped_items},
        ))
        assert wo_result.result["total_work_orders"] > 0
        for wo in wo_result.result["work_orders"]:
            assert wo["estimated_hours"] > 0


class TestE2ESchemaVersionUpgrade:
    def test_schema_migration_backward_compatible(self):
        old_data = {"wingspan": 35.0, "chord_length": 3.5, "sweep_angle": 25.0, "taper_ratio": 0.3, "thickness_ratio": 0.12, "wing_area": 120.0}
        result = SchemaMigrationService.migrate_dict_to_schema("AircraftGeometry", old_data)
        assert result["success"] is True

        schema_obj = AircraftGeometry(**old_data)
        assert schema_obj.wingspan == 35.0
        assert schema_obj.aspect_ratio == pytest.approx(35.0**2 / 120.0, rel=1e-3)

        new_data = schema_obj.model_dump()
        assert "wingspan" in new_data
        assert new_data["wingspan"] == 35.0


class TestE2EPerformanceVerification:
    def test_schema_validation_under_50ms(self):
        import time
        start = time.perf_counter()
        for _ in range(100):
            AircraftGeometry(
                wingspan=35.0, chord_length=3.5, sweep_angle=25.0,
                taper_ratio=0.3, thickness_ratio=0.12, wing_area=120.0,
            )
        elapsed = (time.perf_counter() - start) / 100 * 1000
        assert elapsed < 50.0, f"Schema validation took {elapsed:.3f}ms"

    def test_dof6_step_under_10ms(self):
        import time
        model = DOF6Model(fidelity="Mid")
        model.initialize({"mass": 1500.0, "Ixx": 1000.0, "Iyy": 3000.0, "Izz": 3500.0, "wing_area": 16.0, "wingspan": 10.0, "chord_length": 1.6, "initial_altitude": 1000.0, "initial_speed": 50.0})
        start = time.perf_counter()
        for _ in range(100):
            model.step(0.01)
        elapsed = (time.perf_counter() - start) / 100 * 1000
        assert elapsed < 10.0, f"6DOF step took {elapsed:.3f}ms"

    def test_battery_step_under_5ms(self):
        import time
        model = BatteryModel(fidelity="Mid")
        model.initialize({"capacity_Ah": 100.0, "R0": 0.01, "nominal_voltage": 400.0, "initial_soc": 1.0})
        start = time.perf_counter()
        for _ in range(100):
            model.step(0.01, {"current": 50.0})
        elapsed = (time.perf_counter() - start) / 100 * 1000
        assert elapsed < 5.0, f"Battery step took {elapsed:.3f}ms"

    def test_control_step_under_2ms(self):
        import time
        model = ControlModel(fidelity="Low")
        model.initialize({"kp": 1.0, "ki": 0.1, "kd": 0.01, "dt": 0.01, "output_min": -25.0, "output_max": 25.0})
        start = time.perf_counter()
        for _ in range(100):
            model.step(0.01, {"setpoint": 10.0, "process_variable": 5.0})
        elapsed = (time.perf_counter() - start) / 100 * 1000
        assert elapsed < 2.0, f"Control step took {elapsed:.3f}ms"