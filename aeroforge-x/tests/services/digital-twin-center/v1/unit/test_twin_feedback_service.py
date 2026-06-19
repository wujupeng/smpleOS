import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))

import pytest

from services.digital_twin_center.src.domain.services.v1.twin_sync_service import TwinSyncService
from services.digital_twin_center.src.domain.services.v1.twin_feedback_service import TwinFeedbackService
from services.digital_twin_center.src.domain.entities.v1.design_twin import DesignParameter


class TestTwinFeedbackService:
    @pytest.fixture
    def setup(self):
        sync_service = TwinSyncService()
        feedback_service = TwinFeedbackService(sync_service)
        return sync_service, feedback_service

    @pytest.mark.asyncio
    async def test_feedback_flight_to_design_no_twins(self, setup):
        _, feedback = setup
        result = await feedback.feedback_flight_to_design("SN-001")
        assert result["status"] == "no_twins_available"

    @pytest.mark.asyncio
    async def test_feedback_flight_to_design_with_exceeded_loads(self, setup):
        sync, feedback = setup
        await sync.sync_design_twin("SN-001", [{"name": "wing_root", "value": 100.0, "unit": "kN"}], 1)
        await sync.sync_flight_twin(
            "SN-001",
            {"altitude_ft": 35000},
            loads=[{"component_id": "wing_root", "load_type": "bending", "load_value": 150.0, "unit": "kN", "timestamp": "2024-01-01T10:00:00Z", "exceeds_limit": True}],
        )
        result = await feedback.feedback_flight_to_design("SN-001")
        assert result["feedback_type"] == "flight_to_design"
        assert len(result["feedback_items"]) == 1
        assert result["feedback_items"][0]["actual_load"] == 150.0
        assert result["feedback_items"][0]["design_limit"] == 100.0

    @pytest.mark.asyncio
    async def test_feedback_manufacturing_to_design(self, setup):
        sync, feedback = setup
        await sync.sync_design_twin("SN-001", [{"name": "wingspan", "value": 35.8, "unit": "m"}], 1)
        await sync.sync_manufacturing_twin(
            "SN-001",
            dimensions={"wingspan": 36.0},
            deviations=[{"parameter_name": "wingspan", "design_value": 35.8, "actual_value": 36.0, "tolerance": 0.1, "unit": "m"}],
            process_records=[],
        )
        result = await feedback.feedback_manufacturing_to_design("SN-001")
        assert result["feedback_type"] == "manufacturing_to_design"
        assert len(result["feedback_items"]) == 1
        assert result["feedback_items"][0]["out_of_tolerance"] is True

    @pytest.mark.asyncio
    async def test_feedback_flight_to_maintenance(self, setup):
        sync, feedback = setup
        await sync.sync_flight_twin(
            "SN-001",
            {"altitude_ft": 35000},
            loads=[{"component_id": "wing", "load_type": "bending", "load_value": 150.0, "unit": "kN", "timestamp": "2024-01-01T10:00:00Z", "exceeds_limit": True}],
            systems=[{"system_name": "engine_1", "status": "degraded", "health_percentage": 70.0, "alerts": ["oil_pressure_low"]}],
        )
        await sync.sync_maintenance_twin("SN-001", [], [], [])
        result = await feedback.feedback_flight_to_maintenance("SN-001")
        assert result["feedback_type"] == "flight_to_maintenance"
        assert len(result["recommendations"]) >= 1

    @pytest.mark.asyncio
    async def test_feedback_maintenance_to_manufacturing(self, setup):
        sync, feedback = setup
        await sync.sync_manufacturing_twin(
            "SN-001",
            dimensions={"comp-1": 10.1},
            deviations=[{"parameter_name": "comp-1", "design_value": 10.0, "actual_value": 10.1, "tolerance": 0.05, "unit": "mm"}],
            process_records=[],
        )
        await sync.sync_maintenance_twin(
            "SN-001",
            records=[],
            replacements=[
                {"component_id": "comp-1", "component_name": "Pump", "old_serial": "S1", "new_serial": "S2", "replacement_date": "2024-01-01", "reason": "failure"},
                {"component_id": "comp-1", "component_name": "Pump", "old_serial": "S2", "new_serial": "S3", "replacement_date": "2024-02-01", "reason": "failure"},
                {"component_id": "comp-1", "component_name": "Pump", "old_serial": "S3", "new_serial": "S4", "replacement_date": "2024-03-01", "reason": "failure"},
            ],
            life_updates=[],
        )
        result = await feedback.feedback_maintenance_to_manufacturing("SN-001")
        assert result["feedback_type"] == "maintenance_to_manufacturing"
        assert len(result["feedback_items"]) == 1
        assert result["feedback_items"][0]["recommendation"] == "review_manufacturing_process"