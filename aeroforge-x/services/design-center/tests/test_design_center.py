import pytest

from services.design_center.src.domain.entities.aircraft_spec import AircraftSpec
from services.design_center.src.domain.value_objects.spec_values import AircraftType, PowerType, SpecStatus
from services.design_center.src.domain.services.parameter_validator import ValidationEngine
from services.design_center.src.domain.services.spec_domain_service import SpecDomainService
from services.design_center.src.domain.services.aircraft_type_config import AircraftTypeConfig
from services.design_center.src.domain.services.model_domain_service import ParametricModelGenerator
from services.design_center.src.domain.services.design_rule_engine import DesignRuleEngine


class TestAircraftSpec:
    def test_create_spec(self) -> None:
        spec = AircraftSpec(
            aircraft_type=AircraftType.FIXED_WING,
            payload_kg=500,
            range_km=1000,
            cruise_speed_kmh=250,
            takeoff_distance_m=100,
            power_type=PowerType.ELECTRIC,
            created_by="user-1",
        )
        assert spec.payload_kg == 500
        assert spec.status == SpecStatus.DRAFT
        assert spec.spec_code.startswith("AAF-SPEC-")

    def test_confirm_spec(self) -> None:
        spec = AircraftSpec(payload_kg=120, range_km=200, cruise_speed_kmh=120, takeoff_distance_m=80, created_by="user-1")
        spec.confirm()
        assert spec.status == SpecStatus.CONFIRMED
        assert spec.confirmed_at is not None
        assert len(spec.domain_events) == 1
        assert spec.domain_events[0].event_type == "aircraft.spec.confirmed"

    def test_confirm_non_draft_raises(self) -> None:
        spec = AircraftSpec(payload_kg=120, range_km=200, cruise_speed_kmh=120, takeoff_distance_m=80, created_by="user-1")
        spec.confirm()
        with pytest.raises(ValueError, match="Cannot confirm"):
            spec.confirm()

    def test_freeze_spec(self) -> None:
        spec = AircraftSpec(payload_kg=120, range_km=200, cruise_speed_kmh=120, takeoff_distance_m=80, created_by="user-1")
        spec.confirm()
        spec.freeze()
        assert spec.status == SpecStatus.FROZEN

    def test_update_draft_spec(self) -> None:
        spec = AircraftSpec(payload_kg=120, range_km=200, cruise_speed_kmh=120, takeoff_distance_m=80, created_by="user-1")
        spec.update_parameters(payload_kg=200)
        assert spec.payload_kg == 200

    def test_update_confirmed_spec_raises(self) -> None:
        spec = AircraftSpec(payload_kg=120, range_km=200, cruise_speed_kmh=120, takeoff_distance_m=80, created_by="user-1")
        spec.confirm()
        with pytest.raises(ValueError, match="Cannot update"):
            spec.update_parameters(payload_kg=200)

    def test_to_dict(self) -> None:
        spec = AircraftSpec(payload_kg=120, range_km=200, cruise_speed_kmh=120, takeoff_distance_m=80, created_by="user-1")
        d = spec.to_dict()
        assert d["payload_kg"] == 120
        assert d["status"] == "draft"


class TestValidationEngine:
    def test_complete_valid_params(self) -> None:
        engine = ValidationEngine()
        params = {
            "payload_kg": 120,
            "range_km": 200,
            "cruise_speed_kmh": 120,
            "takeoff_distance_m": 80,
            "power_type": "electric",
        }
        violations = engine.validate(params)
        assert len(violations) == 0

    def test_missing_required_field(self) -> None:
        engine = ValidationEngine()
        violations = engine.validate({"payload_kg": 120})
        assert any(v.parameter == "range_km" for v in violations)

    def test_out_of_range(self) -> None:
        engine = ValidationEngine()
        violations = engine.validate({
            "payload_kg": 120, "range_km": 200, "cruise_speed_kmh": 5000, "takeoff_distance_m": 80, "power_type": "electric",
        })
        assert any(v.parameter == "cruise_speed_kmh" for v in violations)

    def test_electric_high_speed_inconsistency(self) -> None:
        engine = ValidationEngine()
        violations = engine.validate({
            "payload_kg": 120, "range_km": 200, "cruise_speed_kmh": 500, "takeoff_distance_m": 80, "power_type": "electric",
        })
        assert any(v.parameter == "cruise_speed_kmh" and v.severity == "error" for v in violations)


class TestAircraftTypeConfig:
    def test_recommend_evtol(self) -> None:
        config = AircraftTypeConfig()
        result = config.recommend({"power_type": "electric", "cruise_speed_kmh": 120, "payload_kg": 200, "vtol": True})
        assert result["recommended_type"] == AircraftType.EVTOL

    def test_recommend_fixed_wing(self) -> None:
        config = AircraftTypeConfig()
        result = config.recommend({"power_type": "electric", "cruise_speed_kmh": 250, "payload_kg": 500})
        assert result["recommended_type"] == AircraftType.FIXED_WING

    def test_get_template(self) -> None:
        config = AircraftTypeConfig()
        template = config.get_template(AircraftType.FIXED_WING)
        assert "default_params" in template
        assert "aspect_ratio" in template["default_params"]


class TestParametricModelGenerator:
    def test_generate_fixed_wing(self) -> None:
        gen = ParametricModelGenerator()
        result = gen.generate({
            "aircraft_type": "fixed_wing",
            "payload_kg": 120,
            "range_km": 200,
            "cruise_speed_kmh": 120,
            "template": AircraftTypeConfig().get_template("fixed_wing"),
        })
        assert "assembly" in result
        assert "fuselage" in result["assembly"]["components"]
        assert "wing" in result["assembly"]["components"]
        assert "tail" in result["assembly"]["components"]
        assert result["mtow_estimate_kg"] > 0

    def test_generate_evtol(self) -> None:
        gen = ParametricModelGenerator()
        result = gen.generate({
            "aircraft_type": "evtol",
            "payload_kg": 200,
            "range_km": 100,
            "cruise_speed_kmh": 150,
            "template": AircraftTypeConfig().get_template("evtol"),
        })
        assert "assembly" in result


class TestDesignRuleEngine:
    def test_valid_params_no_violations(self) -> None:
        engine = DesignRuleEngine()
        violations = engine.validate({"aspect_ratio": 12, "wing_sweep_deg": 3, "taper_ratio": 0.5, "wing_loading": 200, "fineness_ratio": 8})
        assert len(violations) == 0

    def test_out_of_range_aspect_ratio(self) -> None:
        engine = DesignRuleEngine()
        violations = engine.validate({"aspect_ratio": 30, "wing_sweep_deg": 3, "taper_ratio": 0.5})
        assert any(v["rule_id"] == "AERO-001" for v in violations)

    def test_incremental_validation(self) -> None:
        engine = DesignRuleEngine()
        violations = engine.validate_incremental(
            {"aspect_ratio": 30, "wing_sweep_deg": 3, "taper_ratio": 0.5},
            ["aspect_ratio"],
        )
        assert all(v["parameter"] == "aspect_ratio" for v in violations)


class TestSpecDomainService:
    def test_derive_constraints(self) -> None:
        service = SpecDomainService()
        spec = AircraftSpec(payload_kg=120, range_km=200, cruise_speed_kmh=120, takeoff_distance_m=80, created_by="user-1")
        constraints = service.derive_constraints(spec)
        assert "payload_range_product" in constraints
        assert "endurance_hours" in constraints

    def test_validate_parameters(self) -> None:
        service = SpecDomainService()
        violations = service.validate_parameters({
            "payload_kg": 120, "range_km": 200, "cruise_speed_kmh": 120, "takeoff_distance_m": 80, "power_type": "electric",
        })
        assert isinstance(violations, list)