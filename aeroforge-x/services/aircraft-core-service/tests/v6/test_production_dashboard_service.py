"""AeroForge-X V6.0/V6.1 Unit Tests - ProductionDashboardService
REQ-FACTORY-013~018, REQ-VP-020
"""

import pytest

from src.domain.services.digital_factory.production_dashboard_service import (
    ProductionDashboardService,
    EquipmentOEE,
    AGVDetail,
    AGVFleetStatus,
    BottleneckDetection,
    DeliveryImpactAssessment,
)


@pytest.fixture
def service():
    return ProductionDashboardService()


class TestOEEComputation:

    def test_compute_oee(self, service):
        oee = service.computeOEE(
            equipment_id="EQ-001",
            planned_time=480,
            run_time=432,
            ideal_cycle_time=1.0,
            actual_cycle_time=1.1,
            total_pieces=390,
            good_pieces=370,
        )
        assert isinstance(oee, EquipmentOEE)
        assert 0 <= oee.availability <= 1
        assert 0 <= oee.performance <= 1
        assert 0 <= oee.quality <= 1
        assert 0 <= oee.oee <= 1

    def test_compute_oee_perfect(self, service):
        oee = service.computeOEE(
            equipment_id="EQ-002",
            planned_time=480,
            run_time=480,
            ideal_cycle_time=1.0,
            actual_cycle_time=1.0,
            total_pieces=480,
            good_pieces=480,
        )
        assert oee.availability == 1.0
        assert oee.quality == 1.0

    def test_compute_oee_zero_planned(self, service):
        oee = service.computeOEE("EQ-003", 0, 0, 1.0, 1.0, 0, 0)
        assert oee.availability == 0

    def test_get_equipment_oee(self, service):
        service.computeOEE("EQ-001", 480, 432, 1.0, 1.1, 390, 370)
        oee = service.getEquipmentOEE("EQ-001")
        assert oee.equipment_id == "EQ-001"

    def test_get_nonexistent_oee(self, service):
        oee = service.getEquipmentOEE("FAKE-EQ")
        assert oee.oee == 0.0


class TestAGVFleet:

    def test_update_agv_status(self, service):
        agv = AGVDetail(agv_id="AGV-001", location="Bay-1", task_status="Transporting", battery_level=75.0)
        service.updateAGVStatus(agv)
        status = service.getAGVFleetStatus()
        assert status.total_agvs == 1
        assert status.active_agvs == 1

    def test_agv_fleet_idle(self, service):
        agv = AGVDetail(agv_id="AGV-001", task_status="Idle", battery_level=90.0)
        service.updateAGVStatus(agv)
        status = service.getAGVFleetStatus()
        assert status.idle_agvs == 1

    def test_agv_low_battery(self, service):
        agv = AGVDetail(agv_id="AGV-001", task_status="Idle", battery_level=10.0)
        service.updateAGVStatus(agv)
        status = service.getAGVFleetStatus()
        assert status.low_battery_agvs == 1

    def test_multiple_agvs(self, service):
        service.updateAGVStatus(AGVDetail(agv_id="AGV-001", task_status="Transporting", battery_level=80))
        service.updateAGVStatus(AGVDetail(agv_id="AGV-002", task_status="Idle", battery_level=15))
        status = service.getAGVFleetStatus()
        assert status.total_agvs == 2
        assert status.active_agvs == 1
        assert status.low_battery_agvs == 1


class TestBottleneckDetection:

    def test_detect_bottleneck(self, service):
        service.updateOperationUtilization("OP-001", 0.95)
        result = service.detectBottleneck("LINE-1")
        assert isinstance(result, BottleneckDetection)
        assert result.utilization_rate >= 0.90

    def test_no_bottleneck(self, service):
        service.updateOperationUtilization("OP-001", 0.70)
        result = service.detectBottleneck("LINE-1")
        assert result is None

    def test_no_utilization_data(self, service):
        result = service.detectBottleneck("LINE-1")
        assert result is None


class TestDeliveryImpact:

    def test_compute_delivery_impact(self, service):
        bottleneck = BottleneckDetection(
            constraint_operation_id="OP-001",
            utilization_rate=0.95,
            suggested_capacity_adjustment="Optimize cycle time",
        )
        result = service.computeDeliveryImpact(bottleneck)
        assert isinstance(result, DeliveryImpactAssessment)
        assert result.delivery_delay_days > 0
        assert result.mitigation_recommendation != ""

    def test_severe_delay_mitigation(self, service):
        bottleneck = BottleneckDetection(
            constraint_operation_id="OP-001",
            utilization_rate=0.99,
            suggested_capacity_adjustment="Add parallel station",
        )
        result = service.computeDeliveryImpact(bottleneck)
        assert "overtime" in result.mitigation_recommendation.lower() or "parallel" in result.mitigation_recommendation.lower()


class TestDrillDown:

    def test_drill_down_to_equipment(self, service):
        service.computeOEE("EQ-001", 480, 432, 1.0, 1.1, 390, 370)
        result = service.drillDownToEquipment("EQ-001")
        assert result["equipment_id"] == "EQ-001"
        assert "oee" in result