"""AeroForge-X V6.1 Integration Tests - Production Monitoring Flow
IT-G02: collectData → computeOEE → detectBottleneck → assessDeliveryImpact → updateDashboard
REQ-VP-050
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))

import pytest

from src.domain.services.digital_factory.production_dashboard_service import (
    ProductionDashboardService, AGVDetail,
)


@pytest.fixture
def service():
    return ProductionDashboardService()


class TestProductionMonitoringFlow:

    def test_full_monitoring_flow(self, service):
        oee = service.computeOEE(
            equipment_id="EQ-CNC-001",
            planned_time=480, run_time=432,
            ideal_cycle_time=1.0, actual_cycle_time=1.1,
            total_pieces=390, good_pieces=370,
        )
        assert 0 < oee.oee <= 1.0

        service.updateAGVStatus(AGVDetail(agv_id="AGV-001", task_status="Transporting", battery_level=80))
        service.updateAGVStatus(AGVDetail(agv_id="AGV-002", task_status="Idle", battery_level=15))
        fleet = service.getAGVFleetStatus()
        assert fleet.total_agvs == 2
        assert fleet.low_battery_agvs == 1

        service.updateOperationUtilization("OP-DRILL", 0.95)
        service.updateOperationUtilization("OP-MILL", 0.70)
        bottleneck = service.detectBottleneck("LINE-1")
        assert bottleneck is not None
        assert bottleneck.constraint_operation_id == "OP-DRILL"

        impact = service.computeDeliveryImpact(bottleneck)
        assert impact.delivery_delay_days > 0
        assert impact.mitigation_recommendation != ""

        drill_down = service.drillDownToEquipment("EQ-CNC-001")
        assert drill_down["equipment_id"] == "EQ-CNC-001"
        assert "oee" in drill_down