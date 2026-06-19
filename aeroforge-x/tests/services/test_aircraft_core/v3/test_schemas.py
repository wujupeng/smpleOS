import pytest
import sys
import os
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "services", "aircraft-core-service"))

from src.domain.schemas.aircraft_geometry import AircraftGeometry, WingSubSchema, FuselageSubSchema, TailSubSchema, NacelleSubSchema
from src.domain.schemas.aircraft_structure import AircraftStructure, MaterialProperties
from src.domain.schemas.aircraft_propulsion import AircraftPropulsion, TurbofanParams, TurbopropParams, ElectricParams, HybridParams
from src.domain.schemas.aircraft_avionics import AircraftAvionics, FlightControlParams, NavigationParams, CommunicationParams
from src.domain.schemas.aircraft_flight_envelope import AircraftFlightEnvelope
from src.domain.schemas.aircraft_certification import AircraftCertification
from src.domain.schemas.enums import EngineType, ComplianceStatus, ComplianceMethod, ControlLawType


class TestAircraftGeometry:
    def test_create_valid_geometry(self):
        g = AircraftGeometry(
            wingspan=35.0, chord_length=3.5, sweep_angle=25.0,
            taper_ratio=0.3, thickness_ratio=0.12, wing_area=120.0,
        )
        assert g.wingspan == 35.0
        assert g.chord_length == 3.5
        assert g.aspect_ratio == pytest.approx(35.0**2 / 120.0, rel=1e-3)

    def test_derived_aspect_ratio(self):
        g = AircraftGeometry(
            wingspan=10.0, chord_length=1.0, sweep_angle=0.0,
            taper_ratio=0.5, thickness_ratio=0.1, wing_area=8.0,
        )
        assert g.aspect_ratio == pytest.approx(100.0 / 8.0, rel=1e-3)

    def test_negative_wingspan_fails(self):
        with pytest.raises(Exception):
            AircraftGeometry(
                wingspan=-1.0, chord_length=1.0, sweep_angle=0.0,
                taper_ratio=0.5, thickness_ratio=0.1, wing_area=5.0,
            )

    def test_chord_exceeds_wingspan_fails(self):
        with pytest.raises(Exception):
            AircraftGeometry(
                wingspan=5.0, chord_length=6.0, sweep_angle=0.0,
                taper_ratio=0.5, thickness_ratio=0.1, wing_area=5.0,
            )

    def test_taper_ratio_gt_1_fails(self):
        with pytest.raises(Exception):
            AircraftGeometry(
                wingspan=10.0, chord_length=1.0, sweep_angle=0.0,
                taper_ratio=1.5, thickness_ratio=0.1, wing_area=8.0,
            )

    def test_thickness_ratio_gt_half_fails(self):
        with pytest.raises(Exception):
            AircraftGeometry(
                wingspan=10.0, chord_length=1.0, sweep_angle=0.0,
                taper_ratio=0.5, thickness_ratio=0.6, wing_area=8.0,
            )

    def test_sweep_angle_out_of_range(self):
        with pytest.raises(Exception):
            AircraftGeometry(
                wingspan=10.0, chord_length=1.0, sweep_angle=80.0,
                taper_ratio=0.5, thickness_ratio=0.1, wing_area=8.0,
            )

    def test_wing_sub_schema(self):
        ws = WingSubSchema(naca_number="2412", twist_angle=2.0, control_surface_type="aileron")
        assert ws.naca_number == "2412"
        assert ws.twist_angle == 2.0

    def test_fuselage_sub_schema_fineness_ratio(self):
        fs = FuselageSubSchema(length=30.0, diameter=3.0)
        assert fs.fineness_ratio == pytest.approx(10.0, rel=1e-3)

    def test_tail_sub_schema(self):
        ts = TailSubSchema(tail_type="conventional", tail_area=15.0, tail_arm=12.0)
        assert ts.tail_type == "conventional"

    def test_nacelle_sub_schema(self):
        ns = NacelleSubSchema(nacelle_length=4.0, nacelle_diameter=1.8)
        assert ns.nacelle_length == 4.0

    def test_geometry_with_sub_schemas(self):
        g = AircraftGeometry(
            wingspan=35.0, chord_length=3.5, sweep_angle=25.0,
            taper_ratio=0.3, thickness_ratio=0.12, wing_area=120.0,
            wing_sub_schema=WingSubSchema(naca_number="2412"),
            fuselage_sub_schema=FuselageSubSchema(length=30.0, diameter=3.0),
        )
        assert g.wing_sub_schema.naca_number == "2412"
        assert g.fuselage_sub_schema.fineness_ratio == pytest.approx(10.0, rel=1e-3)


class TestAircraftStructure:
    def test_create_valid_structure(self):
        s = AircraftStructure(
            material_id="AL7075-T6", material_density=2810.0,
            yield_strength=503.0, ultimate_strength=572.0,
            elastic_modulus=71.7, design_weight=500.0,
            rib_spacing=0.5, skin_thickness=2.0,
        )
        assert s.material_id == "AL7075-T6"
        assert s.design_weight == 500.0

    def test_weight_margin_computed(self):
        s = AircraftStructure(
            material_id="AL7075-T6", material_density=2810.0,
            yield_strength=503.0, ultimate_strength=572.0,
            elastic_modulus=71.7, design_weight=500.0,
            manufacturing_weight=480.0,
            rib_spacing=0.5, skin_thickness=2.0,
        )
        assert s.weight_margin == pytest.approx(20.0, rel=1e-3)

    def test_negative_weight_margin_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            AircraftStructure(
                material_id="AL7075-T6", material_density=2810.0,
                yield_strength=503.0, ultimate_strength=572.0,
                elastic_modulus=71.7, design_weight=500.0,
                manufacturing_weight=520.0,
                rib_spacing=0.5, skin_thickness=2.0,
            )
            assert any("overweight" in str(warning.message).lower() or "negative" in str(warning.message).lower() for warning in w)

    def test_material_properties_mismatch_fails(self):
        mp = MaterialProperties(
            density=2810.0, yield_strength=503.0,
            ultimate_strength=572.0, elastic_modulus=71.7, poisson_ratio=0.33,
        )
        with pytest.raises(Exception):
            AircraftStructure(
                material_id="AL7075-T6", material_density=9999.0,
                yield_strength=503.0, ultimate_strength=572.0,
                elastic_modulus=71.7, design_weight=500.0,
                rib_spacing=0.5, skin_thickness=2.0,
                material_properties=mp,
            )

    def test_ultimate_lt_yield_fails(self):
        with pytest.raises(Exception):
            MaterialProperties(
                density=2810.0, yield_strength=600.0,
                ultimate_strength=400.0, elastic_modulus=71.7, poisson_ratio=0.33,
            )

    def test_empty_material_id_fails(self):
        with pytest.raises(Exception):
            AircraftStructure(
                material_id="", material_density=2810.0,
                yield_strength=503.0, ultimate_strength=572.0,
                elastic_modulus=71.7, design_weight=500.0,
                rib_spacing=0.5, skin_thickness=2.0,
            )


class TestAircraftPropulsion:
    def test_turbofan_valid(self):
        p = AircraftPropulsion(
            engine_type=EngineType.Turbofan, max_thrust=120000.0,
            type_specific_params=TurbofanParams(bypass_ratio=8.0, fan_pressure_ratio=1.6, sfc=0.028),
        )
        assert p.engine_type == EngineType.Turbofan
        assert p.type_specific_params.bypass_ratio == 8.0

    def test_turbofan_requires_turbofan_params(self):
        with pytest.raises(Exception):
            AircraftPropulsion(
                engine_type=EngineType.Turbofan, max_thrust=120000.0,
                type_specific_params=ElectricParams(motor_kv=100, battery_capacity=50, battery_voltage=400, max_current=200),
            )

    def test_turboprop_valid(self):
        p = AircraftPropulsion(
            engine_type=EngineType.Turboprop, max_thrust=50000.0,
            type_specific_params=TurbopropParams(propeller_efficiency=0.85, shaft_power=3000, sfc=0.25),
        )
        assert p.engine_type == EngineType.Turboprop

    def test_electric_valid(self):
        p = AircraftPropulsion(
            engine_type=EngineType.Electric, max_thrust=10000.0,
            type_specific_params=ElectricParams(motor_kv=50, battery_capacity=200, battery_voltage=800, max_current=500),
        )
        assert p.engine_type == EngineType.Electric

    def test_hybrid_valid(self):
        p = AircraftPropulsion(
            engine_type=EngineType.Hybrid, max_thrust=80000.0,
            type_specific_params=HybridParams(thermal_power=2000, electric_power=500, battery_capacity=100, battery_voltage=600),
        )
        assert p.engine_type == EngineType.Hybrid

    def test_missing_type_params_fails(self):
        with pytest.raises(Exception):
            AircraftPropulsion(engine_type=EngineType.Turbofan, max_thrust=120000.0)

    def test_turbofan_bypass_lt_1_fails(self):
        with pytest.raises(Exception):
            TurbofanParams(bypass_ratio=0.5, fan_pressure_ratio=1.6, sfc=0.028)

    def test_negative_thrust_fails(self):
        with pytest.raises(Exception):
            AircraftPropulsion(engine_type=EngineType.Turbofan, max_thrust=-100.0)


class TestAircraftAvionics:
    def test_create_valid_avionics(self):
        a = AircraftAvionics(
            flight_control=FlightControlParams(
                elevator_limit=20.0, aileron_limit=20.0, rudder_limit=20.0,
            ),
        )
        assert a.flight_control.elevator_limit == 20.0

    def test_elevator_limit_exceeds_typical_warns(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            AircraftAvionics(
                flight_control=FlightControlParams(
                    elevator_limit=28.0, aileron_limit=20.0, rudder_limit=20.0,
                ),
            )
            assert any("elevator" in str(warning.message).lower() or "25" in str(warning.message) for warning in w)

    def test_certification_warnings_populated(self):
        a = AircraftAvionics(
            flight_control=FlightControlParams(
                elevator_limit=28.0, aileron_limit=28.0, rudder_limit=28.0,
            ),
        )
        assert len(a.certification_warnings) >= 2

    def test_with_navigation_and_comm(self):
        a = AircraftAvionics(
            flight_control=FlightControlParams(elevator_limit=20.0, aileron_limit=20.0, rudder_limit=20.0),
            navigation=NavigationParams(gps_accuracy=2.0, imu_drift=0.01),
            communication=CommunicationParams(comm_frequency=118.0, comm_power=25.0),
        )
        assert a.navigation.gps_accuracy == 2.0
        assert a.communication.comm_frequency == 118.0

    def test_control_limit_gt_30_fails(self):
        with pytest.raises(Exception):
            FlightControlParams(elevator_limit=35.0, aileron_limit=20.0, rudder_limit=20.0)


class TestAircraftFlightEnvelope:
    def test_create_valid_envelope(self):
        e = AircraftFlightEnvelope(
            V_s=60.0, V_A=100.0, V_C=130.0, V_D=180.0,
            h_max=12000.0, n_min=-1.0, n_max=3.5,
            CG_fwd=10.0, CG_aft=15.0,
        )
        assert e.V_s == 60.0
        assert e.V_D == 180.0

    def test_speed_ordering_violated(self):
        with pytest.raises(Exception):
            AircraftFlightEnvelope(
                V_s=100.0, V_A=60.0, V_C=130.0, V_D=180.0,
                h_max=12000.0, n_min=-1.0, n_max=3.5,
                CG_fwd=10.0, CG_aft=15.0,
            )

    def test_n_min_ge_n_max_fails(self):
        with pytest.raises(Exception):
            AircraftFlightEnvelope(
                V_s=60.0, V_A=100.0, V_C=130.0, V_D=180.0,
                h_max=12000.0, n_min=4.0, n_max=3.5,
                CG_fwd=10.0, CG_aft=15.0,
            )

    def test_cg_fwd_ge_cg_aft_fails(self):
        with pytest.raises(Exception):
            AircraftFlightEnvelope(
                V_s=60.0, V_A=100.0, V_C=130.0, V_D=180.0,
                h_max=12000.0, n_min=-1.0, n_max=3.5,
                CG_fwd=15.0, CG_aft=10.0,
            )

    def test_va_close_to_vs_warns(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            AircraftFlightEnvelope(
                V_s=60.0, V_A=63.0, V_C=130.0, V_D=180.0,
                h_max=12000.0, n_min=-1.0, n_max=3.5,
                CG_fwd=10.0, CG_aft=15.0,
            )
            assert any("margin" in str(warning.message).lower() or "close" in str(warning.message).lower() for warning in w)


class TestAircraftCertification:
    def test_create_valid_certification(self):
        c = AircraftCertification(
            clause_number="25.341", clause_title="Gust loads",
            compliance_status=ComplianceStatus.Compliant,
            evidence_ref="RPT-2024-001",
        )
        assert c.clause_number == "25.341"
        assert c.compliance_status == ComplianceStatus.Compliant

    def test_invalid_clause_format_fails(self):
        with pytest.raises(Exception):
            AircraftCertification(clause_number="ABC.123", clause_title="Test")

    def test_compliant_without_evidence_warns(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            AircraftCertification(
                clause_number="25.341", clause_title="Gust loads",
                compliance_status=ComplianceStatus.Compliant,
            )
            assert any("evidence" in str(warning.message).lower() for warning in w)

    def test_non_compliant_triggers_review(self):
        c = AircraftCertification(
            clause_number="25.341", clause_title="Gust loads",
            compliance_status=ComplianceStatus.NonCompliant,
        )
        assert c.compliance_change_triggered is True

    def test_compliant_does_not_trigger_review(self):
        c = AircraftCertification(
            clause_number="25.341", clause_title="Gust loads",
            compliance_status=ComplianceStatus.Compliant,
            evidence_ref="RPT-001",
        )
        assert c.compliance_change_triggered is False

    def test_moc4_without_flight_test_warns(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            AircraftCertification(
                clause_number="25.341", clause_title="Gust loads",
                compliance_method=ComplianceMethod.MOC4,
                evidence_ref="analysis_report_001",
            )
            assert any("flight test" in str(warning.message).lower() for warning in w)

    def test_valid_clause_formats(self):
        for clause in ["25.1", "25.341", "25.341a", "25.341a1"]:
            c = AircraftCertification(clause_number=clause, clause_title="Test")
            assert c.clause_number == clause