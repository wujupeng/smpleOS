import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))

import pytest

from services.digital_twin_center.src.domain.services.v1.twin_sync_service import TwinSyncService
from services.digital_twin_center.src.domain.services.v1.fleet_twin_service import FleetTwinService
from services.digital_twin_center.src.domain.entities.v1.fleet_twin import FleetTwin, FaultStatistics, LifeStatistics, MaintenanceStatistics


class TestFleetTwin:
    def test_create_fleet_twin(self):
        ft = FleetTwin(fleet_id="fleet-001")
        assert ft.fleet_id == "fleet-001"
        assert ft.aircraft_count == 0
        assert ft.status.value == "inactive"

    def test_register_aircraft(self):
        ft = FleetTwin(fleet_id="fleet-001")
        ft.register_aircraft("SN-001")
        ft.register_aircraft("SN-002")
        assert ft.aircraft_count == 2
        assert "SN-001" in ft.registered_aircraft

    def test_unregister_aircraft(self):
        ft = FleetTwin(fleet_id="fleet-001")
        ft.register_aircraft("SN-001")
        ft.unregister_aircraft("SN-001")
        assert ft.aircraft_count == 0

    def test_update_statistics(self):
        ft = FleetTwin(fleet_id="fleet-001")
        ft.register_aircraft("SN-001")
        ft.update_statistics(
            FaultStatistics(total_faults=10, critical_faults=2),
            LifeStatistics(total_components=50, components_due_replacement=5),
            MaintenanceStatistics(total_maintenance_events=20),
        )
        assert ft.fault_statistics.total_faults == 10
        assert ft.status.value == "active"


class TestFleetTwinService:
    @pytest.fixture
    def setup(self):
        sync_service = TwinSyncService()
        fleet_service = FleetTwinService(sync_service)
        return sync_service, fleet_service

    @pytest.mark.asyncio
    async def test_aggregate_fleet_data_empty(self, setup):
        _, fleet_service = setup
        fleet_twin = await fleet_service.aggregate_fleet_data("fleet-001", [])
        assert fleet_twin.aircraft_count == 0

    @pytest.mark.asyncio
    async def test_aggregate_fleet_data_with_aircraft(self, setup):
        sync, fleet_service = setup
        await sync.sync_maintenance_twin(
            "SN-001",
            records=[{"maintenance_id": "M-001", "maintenance_type": "preventive", "description": "A-Check", "performed_date": "2024-01-01", "technician": "TECH-01"}],
            replacements=[],
            life_updates=[
                {"component_id": "comp-1", "component_name": "Pump", "total_life_hours": 10000, "consumed_hours": 5000, "remaining_hours": 5000, "remaining_percentage": 50.0},
                {"component_id": "comp-2", "component_name": "Valve", "total_life_hours": 8000, "consumed_hours": 1000, "remaining_hours": 7000, "remaining_percentage": 87.5},
            ],
        )
        fleet_twin = await fleet_service.aggregate_fleet_data("fleet-001", ["SN-001"])
        assert fleet_twin.aircraft_count == 1
        assert fleet_twin.fault_statistics.total_faults == 1
        assert fleet_twin.life_statistics.total_components == 2

    @pytest.mark.asyncio
    async def test_detect_fleet_anomaly_no_data(self, setup):
        _, fleet_service = setup
        result = await fleet_service.detect_fleet_anomaly("fleet-001")
        assert result["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_detect_fleet_anomaly_nominal(self, setup):
        sync, fleet_service = setup
        await sync.sync_maintenance_twin(
            "SN-001",
            records=[{"maintenance_id": "M-001", "maintenance_type": "preventive", "description": "A-Check", "performed_date": "2024-01-01", "technician": "TECH-01"}],
            replacements=[],
            life_updates=[{"component_id": "comp-1", "component_name": "Pump", "total_life_hours": 10000, "consumed_hours": 2000, "remaining_hours": 8000, "remaining_percentage": 80.0}],
        )
        await fleet_service.aggregate_fleet_data("fleet-001", ["SN-001"])
        result = await fleet_service.detect_fleet_anomaly("fleet-001")
        assert result["status"] == "nominal"

    @pytest.mark.asyncio
    async def test_fleet_reliability_analysis(self, setup):
        sync, fleet_service = setup
        await sync.sync_maintenance_twin(
            "SN-001",
            records=[{"maintenance_id": "M-001", "maintenance_type": "preventive", "description": "A-Check", "performed_date": "2024-01-01", "technician": "TECH-01"}],
            replacements=[],
            life_updates=[{"component_id": "comp-1", "component_name": "Pump", "total_life_hours": 10000, "consumed_hours": 3000, "remaining_hours": 7000, "remaining_percentage": 70.0}],
        )
        await fleet_service.aggregate_fleet_data("fleet-001", ["SN-001"])
        result = await fleet_service.fleet_reliability_analysis("fleet-001")
        assert "reliability_score" in result
        assert "assessment" in result

    @pytest.mark.asyncio
    async def test_predictive_maintenance(self, setup):
        sync, fleet_service = setup
        await sync.sync_maintenance_twin(
            "SN-001",
            records=[],
            replacements=[],
            life_updates=[
                {"component_id": "comp-1", "component_name": "Pump", "total_life_hours": 10000, "consumed_hours": 9000, "remaining_hours": 1000, "remaining_percentage": 10.0},
            ],
        )
        result = await fleet_service.predictive_maintenance("fleet-001", "SN-001")
        assert len(result["predictions"]) == 1
        assert result["predictions"][0]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_aircraft_anonymization(self, setup):
        sync, fleet_service = setup
        await sync.sync_maintenance_twin(
            "SN-001",
            records=[{"maintenance_id": "M-001", "maintenance_type": "preventive", "description": "A-Check", "performed_date": "2024-01-01", "technician": "TECH-01"}],
            replacements=[],
            life_updates=[],
        )
        fleet_twin = await fleet_service.aggregate_fleet_data("fleet-001", ["SN-001"])
        anonymized_keys = list(fleet_twin.fault_statistics.faults_by_aircraft.keys())
        assert "SN-001" not in anonymized_keys
        assert len(anonymized_keys) == 1