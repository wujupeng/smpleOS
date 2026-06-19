"""AeroForge-X V6.1 Integration Tests - Shop Floor Data Flow
IT-G01: registerEquipment → startCollection → validateQuality → syncTwin → detectDeviation → emitEvent
REQ-VP-049
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "physics-twin-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

import pytest

from src.domain.services.digital_factory.shop_floor_data_collector_service import (
    ShopFloorDataCollectorService, EquipmentRegistration, EquipmentType,
    Protocol, ShopFloorDataPoint, OPCUAConfig,
)
from src.domain.services.digital_factory.digital_twin_synchronizer_service import (
    DigitalTwinSynchronizerService,
)
from src.domain.services.digital_factory.shop_floor_event_emitter_service import (
    ShopFloorEventEmitterService, ShopFloorEventType,
)


@pytest.fixture
def collector():
    return ShopFloorDataCollectorService()


@pytest.fixture
def synchronizer():
    return DigitalTwinSynchronizerService()


@pytest.fixture
def emitter():
    return ShopFloorEventEmitterService()


class TestShopFloorDataFlow:

    def test_full_data_flow(self, collector, synchronizer, emitter):
        eq = EquipmentRegistration(
            equipment_id="EQ-CNC-001", equipment_name="CNC Machine 1",
            equipment_type=EquipmentType.CNC, protocol=Protocol.OPC_UA,
        )
        collector.registerEquipment(eq)

        config = OPCUAConfig(server_url="opc.tcp://localhost:4840", node_ids=["ns=2;s=Temp"])
        result = collector.startOPCUACollection("EQ-CNC-001", config)
        assert result["status"] == "Collecting"

        dp = ShopFloorDataPoint(
            timestamp=1000.0, equipment_id="EQ-CNC-001",
            data_type="Temperature", value=150.0, unit="C",
        )
        quality = collector.validateDataQuality(dp)
        assert quality.is_valid is True

        synchronizer.updateTwinState("EQ-CNC-001", {"temp": 150.0})
        synchronizer.updatePhysicalState("EQ-CNC-001", {"temp": 150.0})
        sync_result = synchronizer.syncTwinState("EQ-CNC-001")
        assert sync_result.is_synchronized is True

        synchronizer.updatePhysicalState("EQ-CNC-001", {"temp": 180.0})
        deviation = synchronizer.detectDeviation("EQ-CNC-001")
        assert deviation is not None
        assert deviation.deviation_percentage > 5.0

        receipt = emitter.emitDeviationAlert("EQ-CNC-001", {
            "parameter": "temp", "deviation_pct": deviation.deviation_percentage,
        })
        assert receipt.published is True

    def test_quality_alert_flow(self, collector, emitter):
        eq = EquipmentRegistration(
            equipment_id="EQ-002", equipment_name="Sensor",
            equipment_type=EquipmentType.IOT_SENSOR, protocol=Protocol.MQTT,
        )
        collector.registerEquipment(eq)

        dp = ShopFloorDataPoint(
            timestamp=1000.0, equipment_id="EQ-002",
            data_type="Pressure", value=1e16,
        )
        collector.validateDataQuality(dp)

        receipt = emitter.emitQualityAlert("EQ-002", {"reason": "Out of range"})
        assert receipt.published is True