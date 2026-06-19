import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))

import pytest
from datetime import datetime, timezone

from services.digital_twin_center.src.domain.entities.v1.design_twin import DesignTwin, DesignParameter, DesignTwinStatus
from services.digital_twin_center.src.domain.entities.v1.manufacturing_twin import ManufacturingTwin, DimensionDeviation, ProcessRecord, ManufacturingTwinStatus
from services.digital_twin_center.src.domain.entities.v1.flight_twin import FlightTwin, FlightParameters, StructuralLoad, SystemStatus, FlightTwinStatus
from services.digital_twin_center.src.domain.entities.v1.maintenance_twin import MaintenanceTwin, MaintenanceRecord, ComponentReplacement, RemainingLife, HealthIndicator, MaintenanceTwinStatus


class TestDesignTwin:
    def test_create_design_twin(self):
        twin = DesignTwin(aircraft_serial_number="SN-001")
        assert twin.aircraft_serial_number == "SN-001"
        assert twin.model_version == 1
        assert twin.status == DesignTwinStatus.ACTIVE
        assert len(twin.design_parameters) == 0

    def test_add_design_parameter(self):
        twin = DesignTwin(aircraft_serial_number="SN-001")
        param = DesignParameter(name="wingspan", value=35.8, unit="m", tolerance=0.1)
        twin.add_design_parameter(param)
        assert len(twin.design_parameters) == 1
        assert twin.design_parameters[0].name == "wingspan"
        assert twin.design_parameters[0].value == 35.8

    def test_update_existing_parameter(self):
        twin = DesignTwin(aircraft_serial_number="SN-001")
        twin.add_design_parameter(DesignParameter(name="wingspan", value=35.8, unit="m"))
        twin.add_design_parameter(DesignParameter(name="wingspan", value=36.0, unit="m"))
        assert len(twin.design_parameters) == 1
        assert twin.design_parameters[0].value == 36.0

    def test_update_from_design_change(self):
        twin = DesignTwin(aircraft_serial_number="SN-001")
        params = [DesignParameter(name="length", value=40.0, unit="m")]
        twin.update_from_design_change(params, version=2)
        assert twin.model_version == 2
        assert twin.last_sync_time is not None
        assert twin.status == DesignTwinStatus.ACTIVE

    def test_mark_outdated(self):
        twin = DesignTwin(aircraft_serial_number="SN-001")
        twin.mark_outdated()
        assert twin.status == DesignTwinStatus.OUTDATED

    def test_get_parameter(self):
        twin = DesignTwin(aircraft_serial_number="SN-001")
        twin.add_design_parameter(DesignParameter(name="wingspan", value=35.8, unit="m"))
        param = twin.get_parameter("wingspan")
        assert param is not None
        assert param.value == 35.8
        assert twin.get_parameter("nonexistent") is None

    def test_to_dict(self):
        twin = DesignTwin(aircraft_serial_number="SN-001")
        d = twin.to_dict()
        assert d["aircraft_serial_number"] == "SN-001"
        assert "design_parameters" in d
        assert "model_version" in d


class TestManufacturingTwin:
    def test_create_manufacturing_twin(self):
        twin = ManufacturingTwin(aircraft_serial_number="SN-001")
        assert twin.status == ManufacturingTwinStatus.IN_PRODUCTION
        assert len(twin.deviations) == 0

    def test_record_actual_dimension(self):
        twin = ManufacturingTwin(aircraft_serial_number="SN-001")
        dev = twin.record_actual_dimension("wingspan", 35.85, 35.8, 0.1, "m")
        assert dev.deviation == pytest.approx(0.05)
        assert not dev.out_of_tolerance
        assert "wingspan" in twin.actual_dimensions

    def test_out_of_tolerance(self):
        twin = ManufacturingTwin(aircraft_serial_number="SN-001")
        dev = twin.record_actual_dimension("wingspan", 36.0, 35.8, 0.1, "m")
        assert dev.out_of_tolerance
        oot = twin.get_out_of_tolerance_deviations()
        assert len(oot) == 1

    def test_add_process_record(self):
        twin = ManufacturingTwin(aircraft_serial_number="SN-001")
        record = ProcessRecord(process_step="welding", operator="OP-01", timestamp="2024-01-01T10:00:00Z")
        twin.add_process_record(record)
        assert len(twin.process_records) == 1

    def test_sync_from_manufacturing(self):
        twin = ManufacturingTwin(aircraft_serial_number="SN-001")
        twin.sync_from_manufacturing(
            dimensions={"wingspan": 35.85},
            deviations=[DimensionDeviation("wingspan", 35.8, 35.85, 0.1, "m")],
            process_records=[ProcessRecord("welding", "OP-01", "2024-01-01T10:00:00Z")],
        )
        assert twin.last_sync_time is not None
        assert len(twin.deviations) == 1

    def test_mark_completed(self):
        twin = ManufacturingTwin(aircraft_serial_number="SN-001")
        twin.mark_completed()
        assert twin.status == ManufacturingTwinStatus.COMPLETED


class TestFlightTwin:
    def test_create_flight_twin(self):
        twin = FlightTwin(aircraft_serial_number="SN-001")
        assert twin.status == FlightTwinStatus.GROUNDED
        assert twin.flight_parameters.altitude_ft == 0.0

    def test_update_flight_data(self):
        twin = FlightTwin(aircraft_serial_number="SN-001")
        params = FlightParameters(altitude_ft=35000, airspeed_kts=450, mach_number=0.78)
        twin.update_flight_data(params)
        assert twin.status == FlightTwinStatus.AIRBORNE
        assert twin.flight_parameters.altitude_ft == 35000
        assert twin.last_data_time is not None

    def test_check_data_freshness(self):
        twin = FlightTwin(aircraft_serial_number="SN-001")
        twin.update_flight_data(FlightParameters())
        freshness = twin.check_data_freshness()
        assert freshness["is_fresh"] is True

    def test_get_exceeded_loads(self):
        twin = FlightTwin(aircraft_serial_number="SN-001")
        twin.update_flight_data(
            FlightParameters(),
            loads=[
                StructuralLoad("wing_root", "bending", 150.0, "kN", "2024-01-01T10:00:00Z", exceeds_limit=True),
                StructuralLoad("tail", "shear", 50.0, "kN", "2024-01-01T10:00:00Z", exceeds_limit=False),
            ],
        )
        exceeded = twin.get_exceeded_loads()
        assert len(exceeded) == 1
        assert exceeded[0].component_id == "wing_root"

    def test_get_system_alerts(self):
        twin = FlightTwin(aircraft_serial_number="SN-001")
        twin.update_flight_data(
            FlightParameters(),
            systems=[SystemStatus("engine_1", "degraded", 75.0, ["oil_pressure_low"])],
        )
        alerts = twin.get_system_alerts()
        assert len(alerts) == 1
        assert alerts[0]["system"] == "engine_1"

    def test_mark_grounded(self):
        twin = FlightTwin(aircraft_serial_number="SN-001")
        twin.update_flight_data(FlightParameters())
        twin.mark_grounded()
        assert twin.status == FlightTwinStatus.GROUNDED


class TestMaintenanceTwin:
    def test_create_maintenance_twin(self):
        twin = MaintenanceTwin(aircraft_serial_number="SN-001")
        assert twin.status == MaintenanceTwinStatus.SERVICEABLE

    def test_add_maintenance_record(self):
        twin = MaintenanceTwin(aircraft_serial_number="SN-001")
        record = MaintenanceRecord(
            maintenance_id="M-001",
            maintenance_type="preventive",
            description="A-Check",
            performed_date="2024-01-01",
            technician="TECH-01",
        )
        twin.add_maintenance_record(record)
        assert len(twin.maintenance_history) == 1
        assert twin.last_sync_time is not None

    def test_add_component_replacement(self):
        twin = MaintenanceTwin(aircraft_serial_number="SN-001")
        twin.remaining_life.append(RemainingLife("comp-1", "Hydraulic Pump", 10000, 5000, 5000, 50.0))
        replacement = ComponentReplacement("comp-1", "Hydraulic Pump", "SN-OLD", "SN-NEW", "2024-01-01", "scheduled")
        twin.add_component_replacement(replacement)
        assert len(twin.component_replacements) == 1
        rl = twin.remaining_life[0]
        assert rl.consumed_hours == 0.0
        assert rl.remaining_hours == 10000

    def test_update_remaining_life(self):
        twin = MaintenanceTwin(aircraft_serial_number="SN-001")
        twin.remaining_life.append(RemainingLife("comp-1", "Hydraulic Pump", 10000, 8000, 2000, 20.0))
        twin.update_remaining_life("comp-1", 9500)
        rl = twin.remaining_life[0]
        assert rl.remaining_hours == 500
        assert rl.remaining_percentage == pytest.approx(5.0)
        assert twin.status == MaintenanceTwinStatus.MAINTENANCE_DUE

    def test_update_health_indicator(self):
        twin = MaintenanceTwin(aircraft_serial_number="SN-001")
        twin.update_health_indicator(HealthIndicator("hydraulics", 85.0, "stable", "2024-01-01"))
        assert len(twin.health_indicators) == 1
        twin.update_health_indicator(HealthIndicator("hydraulics", 40.0, "declining", "2024-01-02"))
        assert twin.health_indicators[0].health_score == 40.0
        assert twin.status == MaintenanceTwinStatus.MAINTENANCE_DUE

    def test_get_components_due_for_replacement(self):
        twin = MaintenanceTwin(aircraft_serial_number="SN-001")
        twin.remaining_life.extend([
            RemainingLife("comp-1", "Pump", 10000, 9000, 1000, 10.0),
            RemainingLife("comp-2", "Valve", 10000, 5000, 5000, 50.0),
        ])
        due = twin.get_components_due_for_replacement(threshold_percentage=20.0)
        assert len(due) == 1
        assert due[0].component_id == "comp-1"

    def test_sync_from_maintenance(self):
        twin = MaintenanceTwin(aircraft_serial_number="SN-001")
        twin.sync_from_maintenance(
            records=[MaintenanceRecord("M-001", "preventive", "A-Check", "2024-01-01", "TECH-01")],
            replacements=[],
            life_updates=[RemainingLife("comp-1", "Pump", 10000, 5000, 5000, 50.0)],
        )
        assert len(twin.maintenance_history) == 1
        assert len(twin.remaining_life) == 1