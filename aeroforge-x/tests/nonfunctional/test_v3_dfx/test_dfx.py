import pytest
import time
import math
import sys
import os
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "physics-twin-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "services", "workflow-engine-service"))

from src.domain.schemas.aircraft_geometry import AircraftGeometry
from src.domain.schemas.aircraft_structure import AircraftStructure, MaterialProperties
from src.domain.schemas.aircraft_propulsion import AircraftPropulsion, TurbofanParams
from src.domain.schemas.enums import EngineType
from src.domain.services.unit_conversion_service import UnitConversionService
from src.domain.services.schema_migration_service import SchemaMigrationService
from src.domain.services.domain_event_publisher import DomainEventPublisher, FieldChange
from src.domain.plugins.dof6_model import DOF6Model
from src.domain.plugins.battery_model import BatteryModel
from src.domain.plugins.control_model import ControlModel
from src.domain.handlers.activity_handler_v3 import HandlerInput
from src.domain.handlers.v3_handlers import DesignRuleCheckHandler, FRACASCreateHandler


class TestPerformanceConcurrent:
    def test_concurrent_schema_validation(self):
        start = time.perf_counter()
        for _ in range(100):
            AircraftGeometry(
                wingspan=35.0, chord_length=3.5, sweep_angle=25.0,
                taper_ratio=0.3, thickness_ratio=0.12, wing_area=120.0,
            )
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"100 schema validations took {elapsed:.2f}s"

    def test_concurrent_6dof_simulation(self):
        models = [DOF6Model(fidelity="Low") for _ in range(10)]
        for m in models:
            m.initialize({"mass": 1500.0, "wing_area": 16.0, "initial_altitude": 1000.0, "initial_speed": 50.0})
        start = time.perf_counter()
        for m in models:
            for _ in range(10):
                m.step(0.01)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0

    def test_concurrent_battery_simulation(self):
        models = [BatteryModel(fidelity="Low") for _ in range(20)]
        for m in models:
            m.initialize({"capacity_Ah": 100.0, "R0": 0.01, "nominal_voltage": 400.0, "initial_soc": 1.0})
        start = time.perf_counter()
        for m in models:
            for _ in range(10):
                m.step(0.01, {"current": 50.0})
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0

    def test_concurrent_propagation_handlers(self):
        handler = DesignRuleCheckHandler()
        start = time.perf_counter()
        for _ in range(50):
            handler.execute(HandlerInput(
                model_id="test-001", rule_set_id="rules-v1",
                parameters={"geometry": {"wingspan": 35, "aspect_ratio": 10, "taper_ratio": 0.3, "wing_area": 120}, "structure": {"yield_strength": 503, "design_weight": 500}},
            ))
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0


class TestReliability:
    def test_schema_data_integrity(self):
        g = AircraftGeometry(
            wingspan=35.0, chord_length=3.5, sweep_angle=25.0,
            taper_ratio=0.3, thickness_ratio=0.12, wing_area=120.0,
        )
        data = g.model_dump()
        g2 = AircraftGeometry(**data)
        assert g2.wingspan == g.wingspan
        assert g2.aspect_ratio == g.aspect_ratio

    def test_migration_failure_recovery(self):
        result = SchemaMigrationService.migrate_dict_to_schema("Unknown", {"foo": 1})
        assert result["success"] is False

    def test_numerical_divergence_detection(self):
        model = DOF6Model(fidelity="Detail")
        model.initialize({"mass": 1500.0, "Ixx": 1000.0, "Iyy": 3000.0, "Izz": 3500.0, "wing_area": 16.0, "wingspan": 10.0, "chord_length": 1.6, "initial_altitude": 1000.0, "initial_speed": 50.0})
        model._state.position = [0, 0, 1000]
        model._state.velocity = [2000, 0, 0]
        stability = model.validate_numerical_stability()
        assert stability.is_stable is False

    def test_propagation_chain_robustness(self):
        handler = FRACASCreateHandler()
        result = handler.execute(HandlerInput(model_id="test", parameters={"anomaly_data": {}}))
        assert result.status == "completed"

    def test_event_at_least_once_delivery(self):
        DomainEventPublisher.clear_cache()
        DomainEventPublisher.publish_object_change_event(
            aggregate_id="obj-001",
            changed_fields=[FieldChange(field_path="wingspan", old_value=30.0, new_value=35.0, unit="m", schema_type="AircraftGeometry")],
        )
        cached = DomainEventPublisher.get_cached_events()
        assert len(cached) >= 1


class TestSecurity:
    def test_schema_write_requires_valid_data(self):
        with pytest.raises(Exception):
            AircraftGeometry(wingspan=-1.0, chord_length=1.0, sweep_angle=0.0, taper_ratio=0.5, thickness_ratio=0.1, wing_area=5.0)

    def test_unit_conversion_rejects_incompatible(self):
        with pytest.raises(ValueError):
            UnitConversionService.convert_unit(1.0, "m", "kg")

    def test_handler_input_validation(self):
        handler = DesignRuleCheckHandler()
        errors = handler.validate_input(HandlerInput())
        assert len(errors) > 0

    def test_material_properties_strength_ordering(self):
        with pytest.raises(Exception):
            MaterialProperties(density=2810.0, yield_strength=600.0, ultimate_strength=400.0, elastic_modulus=71.7, poisson_ratio=0.33)


class TestMaintainability:
    def test_schema_health_check(self):
        g = AircraftGeometry(wingspan=35.0, chord_length=3.5, sweep_angle=25.0, taper_ratio=0.3, thickness_ratio=0.12, wing_area=120.0)
        assert g.aspect_ratio > 0

    def test_model_structured_output(self):
        model = DOF6Model(fidelity="Low")
        model.initialize({"mass": 1500.0, "wing_area": 16.0, "initial_altitude": 1000.0, "initial_speed": 50.0})
        result = model.step(0.01)
        assert "state" in result
        assert "forces" in result
        assert "fidelity" in result

    def test_handler_hot_reload_compatible(self):
        h1 = DesignRuleCheckHandler()
        h2 = DesignRuleCheckHandler()
        assert h1.get_handler_name() == h2.get_handler_name()

    def test_supported_fidelities(self):
        model = DOF6Model(fidelity="Low")
        fidelities = model.get_supported_fidelities()
        assert "Low" in fidelities
        assert "Mid" in fidelities
        assert "Detail" in fidelities


class TestCompatibility:
    def test_v2_dict_to_v3_schema_migration(self):
        v2_dict = {"wingspan": 35.0, "chord_length": 3.5, "sweep_angle": 25.0, "taper_ratio": 0.3, "thickness_ratio": 0.12, "wing_area": 120.0}
        result = SchemaMigrationService.migrate_dict_to_schema("AircraftGeometry", v2_dict)
        assert result["success"] is True
        schema_obj = AircraftGeometry(**v2_dict)
        assert schema_obj.wingspan == 35.0

    def test_v2_api_backward_compatible(self):
        v2_dict = {"wingspan": 35.0, "chord_length": 3.5, "sweep_angle": 25.0, "taper_ratio": 0.3, "thickness_ratio": 0.12, "wing_area": 120.0}
        schema_obj = AircraftGeometry(**v2_dict)
        dump = schema_obj.model_dump()
        assert dump["wingspan"] == 35.0
        assert "aspect_ratio" in dump

    def test_si_imperial_unit_conversion(self):
        m_to_ft = UnitConversionService.convert_unit(1.0, "m", "ft")
        assert m_to_ft == pytest.approx(3.28084, rel=1e-3)
        kg_to_lb = UnitConversionService.convert_unit(1.0, "kg", "lb")
        assert kg_to_lb == pytest.approx(2.20462, rel=1e-3)
        MPa_to_psi = UnitConversionService.convert_unit(1.0, "MPa", "psi")
        assert MPa_to_psi == pytest.approx(145.038, rel=1e-2)

    def test_physics_model_fidelity_switch(self):
        model = DOF6Model(fidelity="Low")
        model.initialize({"mass": 1500.0, "wing_area": 16.0, "initial_altitude": 1000.0, "initial_speed": 50.0})
        result_low = model.step(0.01)

        model_mid = DOF6Model(fidelity="Mid")
        model_mid.initialize({"mass": 1500.0, "Ixx": 1000.0, "Iyy": 3000.0, "Izz": 3500.0, "wing_area": 16.0, "wingspan": 10.0, "chord_length": 1.6, "initial_altitude": 1000.0, "initial_speed": 50.0})
        result_mid = model_mid.step(0.01)
        assert result_low["fidelity"] == "Low"
        assert result_mid["fidelity"] == "Mid"