import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

import pytest
from datetime import datetime, timezone, timedelta

from services.digital_twin_center.src.domain.services.v1.twin_sync_service import TwinSyncService
from services.digital_twin_center.src.domain.services.v1.twin_feedback_service import TwinFeedbackService
from services.digital_twin_center.src.domain.services.v1.fleet_twin_service import FleetTwinService


class TestFourStageTwinSyncIntegration:
    @pytest.fixture
    def setup(self):
        sync_service = TwinSyncService()
        feedback_service = TwinFeedbackService(sync_service)
        return sync_service, feedback_service

    @pytest.mark.asyncio
    async def test_full_four_stage_sync_flow(self, setup):
        sync, _ = setup
        aircraft_sn = "SN-INTEG-001"

        design = await sync.sync_design_twin(aircraft_sn, [
            {"name": "wingspan", "value": 35.8, "unit": "m", "tolerance": 0.1},
            {"name": "wing_root_load", "value": 120.0, "unit": "kN"},
        ], model_version=1)
        assert design.model_version == 1

        mfg = await sync.sync_manufacturing_twin(
            aircraft_sn,
            dimensions={"wingspan": 35.95},
            deviations=[{"parameter_name": "wingspan", "design_value": 35.8, "actual_value": 35.95, "tolerance": 0.1, "unit": "m"}],
            process_records=[{"process_step": "assembly", "operator": "OP-01", "timestamp": "2024-01-01T10:00:00Z"}],
        )
        assert len(mfg.deviations) == 1
        oot = mfg.get_out_of_tolerance_deviations()
        assert len(oot) == 1

        flight = await sync.sync_flight_twin(
            aircraft_sn,
            {"altitude_ft": 35000, "airspeed_kts": 450},
            loads=[{"component_id": "wing_root_load", "load_type": "bending", "load_value": 150.0, "unit": "kN", "timestamp": "2024-01-01T10:00:00Z", "exceeds_limit": True}],
        )
        assert len(flight.get_exceeded_loads()) == 1

        maint = await sync.sync_maintenance_twin(
            aircraft_sn,
            records=[{"maintenance_id": "M-001", "maintenance_type": "preventive", "description": "A-Check", "performed_date": "2024-01-01", "technician": "TECH-01"}],
            replacements=[],
            life_updates=[{"component_id": "comp-1", "component_name": "Pump", "total_life_hours": 10000, "consumed_hours": 5000, "remaining_hours": 5000, "remaining_percentage": 50.0}],
        )
        assert len(maint.maintenance_history) == 1

        assert sync.get_design_twin(aircraft_sn) is not None
        assert sync.get_manufacturing_twin(aircraft_sn) is not None
        assert sync.get_flight_twin(aircraft_sn) is not None
        assert sync.get_maintenance_twin(aircraft_sn) is not None


class TestTwinFeedbackLoopIntegration:
    @pytest.fixture
    def setup(self):
        sync_service = TwinSyncService()
        feedback_service = TwinFeedbackService(sync_service)
        return sync_service, feedback_service

    @pytest.mark.asyncio
    async def test_flight_to_design_feedback_loop(self, setup):
        sync, feedback = setup
        aircraft_sn = "SN-FEEDBACK-001"

        await sync.sync_design_twin(aircraft_sn, [
            {"name": "wing_root_load", "value": 120.0, "unit": "kN"},
        ], 1)
        await sync.sync_flight_twin(
            aircraft_sn,
            {"altitude_ft": 35000},
            loads=[{"component_id": "wing_root_load", "load_type": "bending", "load_value": 150.0, "unit": "kN", "timestamp": "2024-01-01T10:00:00Z", "exceeds_limit": True}],
        )
        result = await feedback.feedback_flight_to_design(aircraft_sn)
        assert result["status"] == "action_required"
        assert len(result["feedback_items"]) == 1

    @pytest.mark.asyncio
    async def test_manufacturing_to_design_feedback_loop(self, setup):
        sync, feedback = setup
        aircraft_sn = "SN-FEEDBACK-002"

        await sync.sync_design_twin(aircraft_sn, [
            {"name": "wingspan", "value": 35.8, "unit": "m"},
        ], 1)
        await sync.sync_manufacturing_twin(
            aircraft_sn,
            dimensions={"wingspan": 36.0},
            deviations=[{"parameter_name": "wingspan", "design_value": 35.8, "actual_value": 36.0, "tolerance": 0.1, "unit": "m"}],
            process_records=[],
        )
        result = await feedback.feedback_manufacturing_to_design(aircraft_sn)
        assert result["status"] == "action_required"

    @pytest.mark.asyncio
    async def test_flight_to_maintenance_feedback_loop(self, setup):
        sync, feedback = setup
        aircraft_sn = "SN-FEEDBACK-003"

        await sync.sync_flight_twin(
            aircraft_sn,
            {"altitude_ft": 35000},
            loads=[{"component_id": "wing", "load_type": "bending", "load_value": 150.0, "unit": "kN", "timestamp": "2024-01-01T10:00:00Z", "exceeds_limit": True}],
            systems=[{"system_name": "engine_1", "status": "degraded", "health_percentage": 65.0, "alerts": ["vibration_high"]}],
        )
        await sync.sync_maintenance_twin(aircraft_sn, [], [], [])
        result = await feedback.feedback_flight_to_maintenance(aircraft_sn)
        assert len(result["recommendations"]) >= 1


class TestFleetTwinAggregationIntegration:
    @pytest.fixture
    def setup(self):
        sync_service = TwinSyncService()
        fleet_service = FleetTwinService(sync_service)
        return sync_service, fleet_service

    @pytest.mark.asyncio
    async def test_fleet_aggregation_and_anomaly_detection(self, setup):
        sync, fleet_service = setup
        for sn in ["SN-F-001", "SN-F-002"]:
            await sync.sync_maintenance_twin(
                sn,
                records=[{"maintenance_id": f"M-{sn}", "maintenance_type": "corrective", "description": "Emergency fix", "performed_date": "2024-01-01", "technician": "TECH-01"}],
                replacements=[],
                life_updates=[{"component_id": "comp-1", "component_name": "Pump", "total_life_hours": 10000, "consumed_hours": 9000, "remaining_hours": 1000, "remaining_percentage": 10.0}],
            )

        fleet_twin = await fleet_service.aggregate_fleet_data("fleet-integ", ["SN-F-001", "SN-F-002"])
        assert fleet_twin.aircraft_count == 2
        assert fleet_twin.fault_statistics.total_faults == 2

        anomaly_result = await fleet_service.detect_fleet_anomaly("fleet-integ")
        assert "anomalies" in anomaly_result

    @pytest.mark.asyncio
    async def test_fleet_reliability_and_optimization(self, setup):
        sync, fleet_service = setup
        await sync.sync_maintenance_twin(
            "SN-R-001",
            records=[{"maintenance_id": "M-001", "maintenance_type": "preventive", "description": "A-Check", "performed_date": "2024-01-01", "technician": "TECH-01"}],
            replacements=[],
            life_updates=[{"component_id": "comp-1", "component_name": "Pump", "total_life_hours": 10000, "consumed_hours": 3000, "remaining_hours": 7000, "remaining_percentage": 70.0}],
        )
        await fleet_service.aggregate_fleet_data("fleet-reliab", ["SN-R-001"])

        reliability = await fleet_service.fleet_reliability_analysis("fleet-reliab")
        assert "reliability_score" in reliability

        optimization = await fleet_service.fleet_maintenance_optimization("fleet-reliab")
        assert "recommendations" in optimization


class TestOperationCenterFleetTwinIntegration:
    @pytest.fixture
    def setup(self):
        from services.operation_center.src.domain.services.fleet_management_service import FleetManagementService
        from services.operation_center.src.domain.services.maintenance_scheduling_service import MaintenanceSchedulingService
        from services.operation_center.src.domain.services.flight_data_monitoring_service import FlightDataMonitoringService

        fleet_mgmt = FleetManagementService()
        scheduling = MaintenanceSchedulingService(fleet_mgmt)
        monitoring = FlightDataMonitoringService(fleet_mgmt)
        twin_sync = TwinSyncService()
        fleet_twin = FleetTwinService(twin_sync)
        return fleet_mgmt, scheduling, monitoring, twin_sync, fleet_twin

    @pytest.mark.asyncio
    async def test_aircraft_registration_to_fleet_twin(self, setup):
        fleet_mgmt, _, _, twin_sync, fleet_twin = setup
        await fleet_mgmt.register_aircraft("SN-OPS-001", "A320neo", "fleet-ops")
        await twin_sync.sync_maintenance_twin(
            "SN-OPS-001",
            records=[],
            replacements=[],
            life_updates=[{"component_id": "comp-1", "component_name": "Pump", "total_life_hours": 10000, "consumed_hours": 5000, "remaining_hours": 5000, "remaining_percentage": 50.0}],
        )
        fleet_data = await fleet_twin.aggregate_fleet_data("fleet-ops", ["SN-OPS-001"])
        assert fleet_data.aircraft_count == 1

    @pytest.mark.asyncio
    async def test_flight_monitoring_to_maintenance_scheduling(self, setup):
        fleet_mgmt, scheduling, monitoring, _, _ = setup
        await fleet_mgmt.register_aircraft("SN-OPS-002", "A320neo")
        result = await monitoring.ingest_flight_data("SN-OPS-002", {"altitude_ft": 55000, "g_force": 4.0})
        assert result["anomalies_detected"] > 0
        date = datetime.now(timezone.utc) + timedelta(days=3)
        schedule = await scheduling.create_maintenance_schedule("SN-OPS-002", "emergency_inspection", date, 4.0)
        assert schedule.maintenance_type == "emergency_inspection"