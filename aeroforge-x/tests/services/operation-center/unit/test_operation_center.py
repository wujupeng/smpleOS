import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

import pytest
from datetime import datetime, timezone, timedelta

from services.operation_center.src.domain.entities.aircraft_registration import AircraftRegistration, AircraftStatus
from services.operation_center.src.domain.services.fleet_management_service import FleetManagementService
from services.operation_center.src.domain.services.operation_analytics_service import OperationAnalyticsService
from services.operation_center.src.domain.services.maintenance_scheduling_service import MaintenanceSchedulingService, MaintenanceSchedule
from services.operation_center.src.domain.services.flight_data_monitoring_service import FlightDataMonitoringService


class TestAircraftRegistration:
    def test_create_registration(self):
        reg = AircraftRegistration(aircraft_serial_number="SN-001", model="A320neo")
        assert reg.aircraft_serial_number == "SN-001"
        assert reg.model == "A320neo"
        assert reg.status == AircraftStatus.ACTIVE
        assert reg.total_flight_hours == 0.0

    def test_add_flight_hours(self):
        reg = AircraftRegistration(aircraft_serial_number="SN-001", model="A320neo")
        reg.add_flight_hours(100.5)
        assert reg.total_flight_hours == 100.5
        reg.add_flight_hours(50.0)
        assert reg.total_flight_hours == 150.5

    def test_schedule_maintenance(self):
        reg = AircraftRegistration(aircraft_serial_number="SN-001", model="A320neo")
        date = datetime.now(timezone.utc) + timedelta(days=30)
        reg.schedule_maintenance(date)
        assert reg.next_maintenance_date == date

    def test_set_status(self):
        reg = AircraftRegistration(aircraft_serial_number="SN-001", model="A320neo")
        reg.set_status(AircraftStatus.UNDER_MAINTENANCE)
        assert reg.status == AircraftStatus.UNDER_MAINTENANCE

    def test_assign_to_fleet(self):
        reg = AircraftRegistration(aircraft_serial_number="SN-001", model="A320neo")
        reg.assign_to_fleet("fleet-001")
        assert reg.fleet_id == "fleet-001"

    def test_to_dict(self):
        reg = AircraftRegistration(aircraft_serial_number="SN-001", model="A320neo")
        d = reg.to_dict()
        assert d["aircraft_serial_number"] == "SN-001"
        assert d["model"] == "A320neo"
        assert d["status"] == "active"


class TestFleetManagementService:
    @pytest.fixture
    def service(self):
        return FleetManagementService()

    @pytest.mark.asyncio
    async def test_register_aircraft(self, service):
        reg = await service.register_aircraft("SN-001", "A320neo")
        assert reg.aircraft_serial_number == "SN-001"
        assert reg.model == "A320neo"

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self, service):
        await service.register_aircraft("SN-001", "A320neo")
        with pytest.raises(ValueError, match="already registered"):
            await service.register_aircraft("SN-001", "A320neo")

    @pytest.mark.asyncio
    async def test_track_flight_hours(self, service):
        await service.register_aircraft("SN-001", "A320neo")
        reg = await service.track_flight_hours("SN-001", 100.0)
        assert reg.total_flight_hours == 100.0

    @pytest.mark.asyncio
    async def test_track_flight_hours_unknown_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            await service.track_flight_hours("UNKNOWN", 100.0)

    @pytest.mark.asyncio
    async def test_schedule_maintenance(self, service):
        await service.register_aircraft("SN-001", "A320neo")
        date = datetime.now(timezone.utc) + timedelta(days=30)
        reg = await service.schedule_maintenance("SN-001", date)
        assert reg.next_maintenance_date == date

    @pytest.mark.asyncio
    async def test_get_fleet_status(self, service):
        await service.register_aircraft("SN-001", "A320neo", "fleet-001")
        await service.register_aircraft("SN-002", "B737", "fleet-001")
        status = service.get_fleet_status("fleet-001")
        assert status["total_aircraft"] == 2
        assert status["status_distribution"]["active"] == 2

    @pytest.mark.asyncio
    async def test_list_aircraft(self, service):
        await service.register_aircraft("SN-001", "A320neo", "fleet-001")
        await service.register_aircraft("SN-002", "B737", "fleet-002")
        all_aircraft = service.list_aircraft()
        assert len(all_aircraft) == 2
        fleet_aircraft = service.list_aircraft("fleet-001")
        assert len(fleet_aircraft) == 1


class TestOperationAnalyticsService:
    @pytest.fixture
    def setup(self):
        fleet_service = FleetManagementService()
        analytics_service = OperationAnalyticsService(fleet_service)
        return fleet_service, analytics_service

    @pytest.mark.asyncio
    async def test_utilization_rate(self, setup):
        fleet_service, analytics = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        await fleet_service.track_flight_hours("SN-001", 360.0)
        result = analytics.calculate_utilization_rate(period_days=30)
        assert result["utilization_rate"] >= 0
        assert result["total_flight_hours"] == 360.0

    @pytest.mark.asyncio
    async def test_dispatch_reliability(self, setup):
        fleet_service, analytics = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        await fleet_service.register_aircraft("SN-002", "B737")
        result = analytics.calculate_dispatch_reliability(period_days=30)
        assert result["dispatch_reliability"] > 0
        assert result["active_aircraft"] == 2

    @pytest.mark.asyncio
    async def test_maintenance_cost(self, setup):
        fleet_service, analytics = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        result = analytics.calculate_maintenance_cost(period_days=30)
        assert result["total_cost"] >= 0
        assert "scheduled_cost" in result
        assert "unscheduled_cost" in result

    @pytest.mark.asyncio
    async def test_generate_operation_report(self, setup):
        fleet_service, analytics = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        report = await analytics.generate_operation_report(period_days=30)
        assert report["report_type"] == "operation_analytics"
        assert "utilization" in report
        assert "dispatch_reliability" in report
        assert "maintenance_cost" in report


class TestMaintenanceSchedulingService:
    @pytest.fixture
    def setup(self):
        fleet_service = FleetManagementService()
        scheduling_service = MaintenanceSchedulingService(fleet_service)
        return fleet_service, scheduling_service

    @pytest.mark.asyncio
    async def test_create_maintenance_schedule(self, setup):
        fleet_service, scheduling = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        date = datetime.now(timezone.utc) + timedelta(days=7)
        schedule = await scheduling.create_maintenance_schedule("SN-001", "A-Check", date, 8.0)
        assert schedule.aircraft_sn == "SN-001"
        assert schedule.maintenance_type == "A-Check"
        assert schedule.status == "planned"

    @pytest.mark.asyncio
    async def test_adjust_schedule(self, setup):
        fleet_service, scheduling = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        date = datetime.now(timezone.utc) + timedelta(days=7)
        schedule = await scheduling.create_maintenance_schedule("SN-001", "A-Check", date)
        new_date = datetime.now(timezone.utc) + timedelta(days=14)
        adjusted = await scheduling.adjust_schedule(schedule.schedule_id, new_date, "parts delay")
        assert adjusted.scheduled_date == new_date
        assert adjusted.adjustment_reason == "parts delay"

    @pytest.mark.asyncio
    async def test_get_schedules_for_aircraft(self, setup):
        fleet_service, scheduling = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        date = datetime.now(timezone.utc) + timedelta(days=7)
        await scheduling.create_maintenance_schedule("SN-001", "A-Check", date)
        schedules = scheduling.get_schedules_for_aircraft("SN-001")
        assert len(schedules) == 1

    @pytest.mark.asyncio
    async def test_check_high_frequency_maintenance(self, setup):
        fleet_service, scheduling = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        result = scheduling.check_high_frequency_maintenance("SN-001", threshold=3)
        assert result["is_high_frequency"] is False


class TestFlightDataMonitoringService:
    @pytest.fixture
    def setup(self):
        fleet_service = FleetManagementService()
        monitoring_service = FlightDataMonitoringService(fleet_service)
        return fleet_service, monitoring_service

    @pytest.mark.asyncio
    async def test_ingest_flight_data(self, setup):
        fleet_service, monitoring = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        result = await monitoring.ingest_flight_data("SN-001", {"altitude_ft": 35000, "airspeed_kts": 450})
        assert result["ingested"] is True
        assert result["anomalies_detected"] == 0

    @pytest.mark.asyncio
    async def test_ingest_with_anomaly(self, setup):
        fleet_service, monitoring = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        result = await monitoring.ingest_flight_data("SN-001", {"altitude_ft": 55000, "g_force": 4.0})
        assert result["anomalies_detected"] == 2

    @pytest.mark.asyncio
    async def test_monitor_flight_status(self, setup):
        fleet_service, monitoring = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        await monitoring.ingest_flight_data("SN-001", {"altitude_ft": 35000})
        status = monitoring.monitor_flight_status("SN-001")
        assert status["aircraft_sn"] == "SN-001"
        assert status["data_points_count"] == 1

    @pytest.mark.asyncio
    async def test_get_alerts(self, setup):
        fleet_service, monitoring = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        await monitoring.ingest_flight_data("SN-001", {"altitude_ft": 55000})
        alerts = monitoring.get_alerts("SN-001")
        assert len(alerts) >= 1

    @pytest.mark.asyncio
    async def test_get_flight_data(self, setup):
        fleet_service, monitoring = setup
        await fleet_service.register_aircraft("SN-001", "A320neo")
        await monitoring.ingest_flight_data("SN-001", {"altitude_ft": 35000})
        data = monitoring.get_flight_data("SN-001")
        assert len(data) == 1