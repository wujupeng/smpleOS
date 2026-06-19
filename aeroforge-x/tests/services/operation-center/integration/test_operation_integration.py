import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

import pytest
from datetime import datetime, timezone, timedelta

from services.operation_center.src.domain.services.fleet_management_service import FleetManagementService
from services.operation_center.src.domain.services.operation_analytics_service import OperationAnalyticsService
from services.operation_center.src.domain.services.maintenance_scheduling_service import MaintenanceSchedulingService
from services.operation_center.src.domain.services.flight_data_monitoring_service import FlightDataMonitoringService


class TestOperationCenterIntegration:
    @pytest.fixture
    def setup(self):
        fleet_mgmt = FleetManagementService()
        analytics = OperationAnalyticsService(fleet_mgmt)
        scheduling = MaintenanceSchedulingService(fleet_mgmt)
        monitoring = FlightDataMonitoringService(fleet_mgmt)
        return fleet_mgmt, analytics, scheduling, monitoring

    @pytest.mark.asyncio
    async def test_full_operation_workflow(self, setup):
        fleet_mgmt, analytics, scheduling, monitoring = setup

        await fleet_mgmt.register_aircraft("SN-INT-001", "A320neo", "fleet-001")
        await fleet_mgmt.register_aircraft("SN-INT-002", "B737", "fleet-001")

        await fleet_mgmt.track_flight_hours("SN-INT-001", 500.0)
        await fleet_mgmt.track_flight_hours("SN-INT-002", 300.0)

        date = datetime.now(timezone.utc) + timedelta(days=7)
        await scheduling.create_maintenance_schedule("SN-INT-001", "A-Check", date, 8.0)

        await monitoring.ingest_flight_data("SN-INT-001", {"altitude_ft": 35000, "airspeed_kts": 450})
        await monitoring.ingest_flight_data("SN-INT-002", {"altitude_ft": 28000, "airspeed_kts": 380})

        fleet_status = fleet_mgmt.get_fleet_status("fleet-001")
        assert fleet_status["total_aircraft"] == 2
        assert fleet_status["total_flight_hours"] == 800.0

        utilization = analytics.calculate_utilization_rate("fleet-001", 30)
        assert utilization["utilization_rate"] >= 0

        dispatch = analytics.calculate_dispatch_reliability("fleet-001", 30)
        assert dispatch["dispatch_reliability"] > 0

        cost = analytics.calculate_maintenance_cost("fleet-001", 30)
        assert cost["total_cost"] >= 0

        report = await analytics.generate_operation_report("fleet-001", 30)
        assert report["report_type"] == "operation_analytics"

    @pytest.mark.asyncio
    async def test_flight_anomaly_triggers_maintenance(self, setup):
        fleet_mgmt, _, scheduling, monitoring = setup

        await fleet_mgmt.register_aircraft("SN-ANOM-001", "A320neo")
        result = await monitoring.ingest_flight_data("SN-ANOM-001", {"altitude_ft": 55000, "g_force": 4.0})
        assert result["anomalies_detected"] > 0

        alerts = monitoring.get_alerts("SN-ANOM-001")
        assert len(alerts) > 0

        date = datetime.now(timezone.utc) + timedelta(days=2)
        schedule = await scheduling.create_maintenance_schedule("SN-ANOM-001", "emergency_inspection", date, 4.0)
        assert schedule.maintenance_type == "emergency_inspection"

    @pytest.mark.asyncio
    async def test_high_frequency_maintenance_detection(self, setup):
        fleet_mgmt, _, scheduling, _ = setup

        await fleet_mgmt.register_aircraft("SN-FREQ-001", "A320neo")
        date = datetime.now(timezone.utc)
        for i in range(4):
            await scheduling.create_maintenance_schedule(
                "SN-FREQ-001",
                f"unscheduled-{i}",
                date - timedelta(days=30 - i * 7),
                4.0,
            )

        result = scheduling.check_high_frequency_maintenance("SN-FREQ-001", threshold=3, period_days=90)
        assert result["is_high_frequency"] is True
        assert result["recommendation"] == "adjust_preventive_maintenance_plan"