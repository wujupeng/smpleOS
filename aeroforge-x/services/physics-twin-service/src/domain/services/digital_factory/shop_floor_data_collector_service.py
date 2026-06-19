"""AeroForge-X v6.0 ShopFloorDataCollectorService

Manages real-time shop floor data collection via OPC-UA/MQTT protocols,
data quality validation, and configurable sampling rates.
REQ-FACTORY-001~006, REQ-DFX-V6-009, REQ-DFX-V6-012
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EquipmentType(str, Enum):
    PLC = "PLC"
    CNC = "CNC"
    ROBOT = "Robot"
    AGV = "AGV"
    IOT_SENSOR = "IoTSensor"


class Protocol(str, Enum):
    OPC_UA = "OPC-UA"
    MQTT = "MQTT"


class EquipmentStatus(str, Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    ERROR = "Error"


class QualityFlag(str, Enum):
    GOOD = "Good"
    SUSPECT = "Suspect"
    BAD = "Bad"


@dataclass
class EquipmentRegistration:
    equipment_id: str
    equipment_name: str
    equipment_type: EquipmentType
    protocol: Protocol
    sampling_rate_ms: int = 1000
    location: str = ""
    status: EquipmentStatus = EquipmentStatus.OFFLINE
    connection_config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "equipment_id": self.equipment_id,
            "equipment_name": self.equipment_name,
            "equipment_type": self.equipment_type.value,
            "protocol": self.protocol.value,
            "sampling_rate_ms": self.sampling_rate_ms,
            "location": self.location,
            "status": self.status.value,
            "connection_config": self.connection_config,
        }


@dataclass
class ShopFloorDataPoint:
    timestamp: float
    equipment_id: str
    data_type: str
    value: float
    unit: str = ""
    quality_flag: QualityFlag = QualityFlag.GOOD

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "equipment_id": self.equipment_id,
            "data_type": self.data_type,
            "value": self.value,
            "unit": self.unit,
            "quality_flag": self.quality_flag.value,
        }


@dataclass
class DataQualityResult:
    is_valid: bool
    validation_failures: list[str] = field(default_factory=list)
    last_known_good_value: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "validation_failures": self.validation_failures,
            "last_known_good_value": self.last_known_good_value,
        }


@dataclass
class OPCUAConfig:
    server_url: str
    node_ids: list[str] = field(default_factory=list)
    security_mode: str = "None"


@dataclass
class MQTTConfig:
    broker_host: str
    broker_port: int = 1883
    topic: str = ""
    qos: int = 1


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout_s: float = 300.0) -> None:
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout_s = recovery_timeout_s
        self._last_failure_time: Optional[float] = None
        self._is_open = False

    def record_success(self) -> None:
        self._failure_count = 0
        self._is_open = False

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._is_open = True

    def is_available(self) -> bool:
        if not self._is_open:
            return True
        if self._last_failure_time and (time.monotonic() - self._last_failure_time) > self._recovery_timeout_s:
            self._is_open = False
            self._failure_count = 0
            return True
        return False


SAMPLING_RATE_PRESETS = {
    EquipmentType.PLC: 100,
    EquipmentType.CNC: 100,
    EquipmentType.ROBOT: 100,
    EquipmentType.AGV: 1000,
    EquipmentType.IOT_SENSOR: 10000,
}


class ShopFloorDataCollectorService:

    def __init__(self) -> None:
        self._equipment: dict[str, EquipmentRegistration] = {}
        self._last_known_good: dict[str, float] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._data_buffer: list[ShopFloorDataPoint] = []

    def registerEquipment(self, equipment: EquipmentRegistration) -> str:
        if equipment.equipment_id in self._equipment:
            raise ValueError(f"Equipment already registered: {equipment.equipment_id}")

        if equipment.sampling_rate_ms == 1000:
            preset = SAMPLING_RATE_PRESETS.get(equipment.equipment_type, 1000)
            equipment.sampling_rate_ms = preset

        self._equipment[equipment.equipment_id] = equipment
        self._circuit_breakers[equipment.equipment_id] = CircuitBreaker()
        return equipment.equipment_id

    def startOPCUACollection(
        self, equipment_id: str, config: OPCUAConfig
    ) -> dict:
        if equipment_id not in self._equipment:
            raise ValueError(f"Equipment not found: {equipment_id}")

        equipment = self._equipment[equipment_id]
        if equipment.protocol != Protocol.OPC_UA:
            raise ValueError(f"Equipment {equipment_id} is not OPC-UA protocol")

        equipment.status = EquipmentStatus.ONLINE
        equipment.connection_config = {
            "server_url": config.server_url,
            "node_ids": config.node_ids,
            "security_mode": config.security_mode,
        }

        return {
            "equipment_id": equipment_id,
            "status": "Collecting",
            "protocol": "OPC-UA",
            "sampling_rate_ms": equipment.sampling_rate_ms,
        }

    def startMQTTCollection(
        self, equipment_id: str, config: MQTTConfig
    ) -> dict:
        if equipment_id not in self._equipment:
            raise ValueError(f"Equipment not found: {equipment_id}")

        equipment = self._equipment[equipment_id]
        if equipment.protocol != Protocol.MQTT:
            raise ValueError(f"Equipment {equipment_id} is not MQTT protocol")

        equipment.status = EquipmentStatus.ONLINE
        equipment.connection_config = {
            "broker_host": config.broker_host,
            "broker_port": config.broker_port,
            "topic": config.topic,
            "qos": config.qos,
        }

        return {
            "equipment_id": equipment_id,
            "status": "Collecting",
            "protocol": "MQTT",
            "sampling_rate_ms": equipment.sampling_rate_ms,
        }

    def validateDataQuality(self, data_point: ShopFloorDataPoint) -> DataQualityResult:
        failures = []
        equipment = self._equipment.get(data_point.equipment_id)

        if not equipment:
            failures.append("Unknown equipment")
            return DataQualityResult(is_valid=False, validation_failures=failures)

        if data_point.value is None or abs(data_point.value) > 1e15:
            failures.append("Range check failed")

        last_good = self._last_known_good.get(data_point.equipment_id)
        if last_good is not None and abs(data_point.value - last_good) > abs(last_good) * 10:
            failures.append("Rate-of-change check failed")

        if equipment.status == EquipmentStatus.ERROR:
            failures.append("Equipment status inconsistency")

        is_valid = len(failures) == 0
        result = DataQualityResult(
            is_valid=is_valid,
            validation_failures=failures,
            last_known_good_value=last_good,
        )

        if is_valid:
            self._last_known_good[data_point.equipment_id] = data_point.value
            data_point.quality_flag = QualityFlag.GOOD
        else:
            data_point.quality_flag = QualityFlag.BAD

        self._data_buffer.append(data_point)
        return result

    def handleQualityFailure(self, data_point: ShopFloorDataPoint) -> dict:
        result = self.validateDataQuality(data_point)

        if not result.is_valid:
            cb = self._circuit_breakers.get(data_point.equipment_id)
            if cb:
                cb.record_failure()

            last_good = self._last_known_good.get(data_point.equipment_id)
            return {
                "action": "UseLastKnownGood",
                "equipment_id": data_point.equipment_id,
                "failed_value": data_point.value,
                "last_known_good": last_good,
                "validation_failures": result.validation_failures,
            }

        cb = self._circuit_breakers.get(data_point.equipment_id)
        if cb:
            cb.record_success()

        return {
            "action": "Accept",
            "equipment_id": data_point.equipment_id,
            "value": data_point.value,
        }

    def configureSamplingRates(
        self, equipment_type: EquipmentType, rate_ms: int
    ) -> dict:
        SAMPLING_RATE_PRESETS[equipment_type] = rate_ms
        updated = 0
        for eq in self._equipment.values():
            if eq.equipment_type == equipment_type:
                eq.sampling_rate_ms = rate_ms
                updated += 1
        return {
            "equipment_type": equipment_type.value,
            "new_rate_ms": rate_ms,
            "updated_equipment_count": updated,
        }

    def getEquipment(self, equipment_id: str) -> Optional[EquipmentRegistration]:
        return self._equipment.get(equipment_id)