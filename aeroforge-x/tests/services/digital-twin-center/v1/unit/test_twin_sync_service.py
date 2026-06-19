import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))

import pytest
from datetime import datetime, timezone

from services.digital_twin_center.src.domain.services.v1.twin_sync_service import TwinSyncService, ConflictResolution
from services.digital_twin_center.src.domain.entities.v1.design_twin import DesignParameter


class TestTwinSyncService:
    @pytest.fixture
    def service(self):
        return TwinSyncService()

    @pytest.mark.asyncio
    async def test_sync_design_twin(self, service):
        twin = await service.sync_design_twin(
            aircraft_sn="SN-001",
            parameters=[
                {"name": "wingspan", "value": 35.8, "unit": "m", "tolerance": 0.1},
                {"name": "length", "value": 40.0, "unit": "m"},
            ],
            model_version=2,
        )
        assert twin.aircraft_serial_number == "SN-001"
        assert twin.model_version == 2
        assert len(twin.design_parameters) == 2
        assert twin.last_sync_time is not None

    @pytest.mark.asyncio
    async def test_sync_manufacturing_twin(self, service):
        twin = await service.sync_manufacturing_twin(
            aircraft_sn="SN-001",
            dimensions={"wingspan": 35.85},
            deviations=[{"parameter_name": "wingspan", "design_value": 35.8, "actual_value": 35.85, "tolerance": 0.1, "unit": "m"}],
            process_records=[{"process_step": "welding", "operator": "OP-01", "timestamp": "2024-01-01T10:00:00Z"}],
        )
        assert len(twin.deviations) == 1
        assert twin.last_sync_time is not None

    @pytest.mark.asyncio
    async def test_sync_flight_twin(self, service):
        twin = await service.sync_flight_twin(
            aircraft_sn="SN-001",
            flight_params={"altitude_ft": 35000, "airspeed_kts": 450},
            loads=[{"component_id": "wing", "load_type": "bending", "load_value": 120.0, "unit": "kN", "timestamp": "2024-01-01T10:00:00Z", "exceeds_limit": False}],
        )
        assert twin.flight_parameters.altitude_ft == 35000
        assert len(twin.structural_loads) == 1

    @pytest.mark.asyncio
    async def test_sync_maintenance_twin(self, service):
        twin = await service.sync_maintenance_twin(
            aircraft_sn="SN-001",
            records=[{"maintenance_id": "M-001", "maintenance_type": "preventive", "description": "A-Check", "performed_date": "2024-01-01", "technician": "TECH-01"}],
            replacements=[],
            life_updates=[{"component_id": "comp-1", "component_name": "Pump", "total_life_hours": 10000, "consumed_hours": 5000, "remaining_hours": 5000, "remaining_percentage": 50.0}],
        )
        assert len(twin.maintenance_history) == 1
        assert len(twin.remaining_life) == 1

    @pytest.mark.asyncio
    async def test_get_twin_returns_none_for_unknown(self, service):
        assert service.get_design_twin("UNKNOWN") is None
        assert service.get_manufacturing_twin("UNKNOWN") is None
        assert service.get_flight_twin("UNKNOWN") is None
        assert service.get_maintenance_twin("UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_get_twin_after_sync(self, service):
        await service.sync_design_twin("SN-001", [{"name": "wingspan", "value": 35.8, "unit": "m"}], 1)
        twin = service.get_design_twin("SN-001")
        assert twin is not None
        assert twin.aircraft_serial_number == "SN-001"

    @pytest.mark.asyncio
    async def test_check_data_lag(self, service):
        await service.sync_design_twin("SN-001", [{"name": "wingspan", "value": 35.8, "unit": "m"}], 1)
        lag_info = service.check_data_lag("SN-001")
        assert "design" in lag_info["twins"]
        assert lag_info["twins"]["design"]["lagged"] is False

    def test_conflict_resolution_measured_priority(self):
        result = ConflictResolution.resolve({"measured": True, "design": True, "inferred": True})
        assert result == "measured"

    def test_conflict_resolution_design_over_inferred(self):
        result = ConflictResolution.resolve({"design": True, "inferred": True})
        assert result == "design"

    def test_conflict_resolution_inferred_only(self):
        result = ConflictResolution.resolve({"inferred": True})
        assert result == "inferred"

    @pytest.mark.asyncio
    async def test_resolve_conflict(self, service):
        result = service.resolve_conflict("SN-001", "wingspan", {"measured": 35.85, "design": 35.8})
        assert result["resolved_source"] == "measured"
        assert result["resolved_value"] == 35.85