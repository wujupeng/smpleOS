"""AeroForge-X V6.0/V6.1 Unit Tests - ShopFloorDataCollectorService
REQ-FACTORY-001~006, REQ-VP-020
"""

import pytest

from src.domain.services.digital_factory.shop_floor_data_collector_service import (
    ShopFloorDataCollectorService,
    EquipmentRegistration,
    EquipmentType,
    Protocol,
    EquipmentStatus,
    ShopFloorDataPoint,
    QualityFlag,
    DataQualityResult,
    OPCUAConfig,
    MQTTConfig,
    CircuitBreaker,
)


@pytest.fixture
def service():
    return ShopFloorDataCollectorService()


@pytest.fixture
def plc_equipment():
    return EquipmentRegistration(
        equipment_id="EQ-PLC-001",
        equipment_name="CNC Machine 1",
        equipment_type=EquipmentType.CNC,
        protocol=Protocol.OPC_UA,
    )


@pytest.fixture
def mqtt_equipment():
    return EquipmentRegistration(
        equipment_id="EQ-IOT-001",
        equipment_name="IoT Sensor Array",
        equipment_type=EquipmentType.IOT_SENSOR,
        protocol=Protocol.MQTT,
    )


class TestRegisterEquipment:

    def test_register_equipment(self, service, plc_equipment):
        result = service.registerEquipment(plc_equipment)
        assert result == "EQ-PLC-001"

    def test_register_duplicate_raises(self, service, plc_equipment):
        service.registerEquipment(plc_equipment)
        with pytest.raises(ValueError, match="already registered"):
            service.registerEquipment(plc_equipment)

    def test_default_sampling_rate_applied(self, service, plc_equipment):
        service.registerEquipment(plc_equipment)
        eq = service.getEquipment("EQ-PLC-001")
        assert eq.sampling_rate_ms == 100


class TestOPCUACollection:

    def test_start_opcua_collection(self, service, plc_equipment):
        service.registerEquipment(plc_equipment)
        config = OPCUAConfig(server_url="opc.tcp://localhost:4840", node_ids=["ns=2;s=Temp"])
        result = service.startOPCUACollection("EQ-PLC-001", config)
        assert result["status"] == "Collecting"
        assert result["protocol"] == "OPC-UA"

    def test_opcua_wrong_protocol_raises(self, service, mqtt_equipment):
        service.registerEquipment(mqtt_equipment)
        config = OPCUAConfig(server_url="opc.tcp://localhost:4840")
        with pytest.raises(ValueError, match="not OPC-UA"):
            service.startOPCUACollection("EQ-IOT-001", config)

    def test_opcua_nonexistent_equipment_raises(self, service):
        config = OPCUAConfig(server_url="opc.tcp://localhost:4840")
        with pytest.raises(ValueError, match="not found"):
            service.startOPCUACollection("FAKE-EQ", config)


class TestMQTTCollection:

    def test_start_mqtt_collection(self, service, mqtt_equipment):
        service.registerEquipment(mqtt_equipment)
        config = MQTTConfig(broker_host="localhost", topic="factory/sensors")
        result = service.startMQTTCollection("EQ-IOT-001", config)
        assert result["status"] == "Collecting"
        assert result["protocol"] == "MQTT"

    def test_mqtt_wrong_protocol_raises(self, service, plc_equipment):
        service.registerEquipment(plc_equipment)
        config = MQTTConfig(broker_host="localhost")
        with pytest.raises(ValueError, match="not MQTT"):
            service.startMQTTCollection("EQ-PLC-001", config)


class TestDataQualityValidation:

    def test_validate_good_data(self, service, plc_equipment):
        service.registerEquipment(plc_equipment)
        dp = ShopFloorDataPoint(
            timestamp=1000.0, equipment_id="EQ-PLC-001",
            data_type="Temperature", value=25.5, unit="C"
        )
        result = service.validateDataQuality(dp)
        assert isinstance(result, DataQualityResult)
        assert result.is_valid is True

    def test_validate_unknown_equipment(self, service):
        dp = ShopFloorDataPoint(
            timestamp=1000.0, equipment_id="FAKE-EQ",
            data_type="Temp", value=25.0
        )
        result = service.validateDataQuality(dp)
        assert result.is_valid is False

    def test_validate_extreme_value(self, service, plc_equipment):
        service.registerEquipment(plc_equipment)
        dp = ShopFloorDataPoint(
            timestamp=1000.0, equipment_id="EQ-PLC-001",
            data_type="Temp", value=1e16
        )
        result = service.validateDataQuality(dp)
        assert result.is_valid is False


class TestQualityFailureHandling:

    def test_handle_quality_failure(self, service, plc_equipment):
        service.registerEquipment(plc_equipment)
        dp = ShopFloorDataPoint(
            timestamp=1000.0, equipment_id="EQ-PLC-001",
            data_type="Temp", value=1e16
        )
        result = service.handleQualityFailure(dp)
        assert result["action"] == "UseLastKnownGood"

    def test_handle_good_data(self, service, plc_equipment):
        service.registerEquipment(plc_equipment)
        dp = ShopFloorDataPoint(
            timestamp=1000.0, equipment_id="EQ-PLC-001",
            data_type="Temp", value=25.0
        )
        result = service.handleQualityFailure(dp)
        assert result["action"] == "Accept"


class TestCircuitBreaker:

    def test_circuit_breaker_opens(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout_s=300)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_available() is False

    def test_circuit_breaker_closes_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        cb.record_success()
        assert cb.is_available() is True


class TestSamplingRates:

    def test_configure_sampling_rates(self, service, plc_equipment):
        service.registerEquipment(plc_equipment)
        result = service.configureSamplingRates(EquipmentType.CNC, 50)
        assert result["new_rate_ms"] == 50
        assert result["updated_equipment_count"] == 1