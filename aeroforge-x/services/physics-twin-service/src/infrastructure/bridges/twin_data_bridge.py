from abc import ABC, abstractmethod
from typing import Any


class TwinDataBridge(ABC):

    @abstractmethod
    async def bridge(self, v1_data: dict[str, Any]) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_source_twin_type(self) -> str:
        pass


class DesignTwinBridge(TwinDataBridge):

    async def bridge(self, v1_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "target": "PhysicsModel",
            "parameter_mappings": v1_data.get("design_parameters", {}),
            "geometry_ref": v1_data.get("geometry_ref", ""),
        }

    def get_source_twin_type(self) -> str:
        return "DesignTwin"


class ManufacturingTwinBridge(TwinDataBridge):

    async def bridge(self, v1_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "target": "PhysicsModel",
            "parameter_corrections": v1_data.get("manufacturing_deviations", {}),
            "process_data": v1_data.get("process_data", {}),
        }

    def get_source_twin_type(self) -> str:
        return "ManufacturingTwin"


class FlightTwinBridge(TwinDataBridge):

    async def bridge(self, v1_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "target": "DigitalTwinRuntime",
            "sensor_data_stream": v1_data.get("flight_data", {}),
            "sensor_mappings": v1_data.get("sensor_mappings", {}),
        }

    def get_source_twin_type(self) -> str:
        return "FlightTwin"


class MaintenanceTwinBridge(TwinDataBridge):

    async def bridge(self, v1_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "target": "TwinCalibration",
            "degradation_data": v1_data.get("degradation_data", {}),
            "maintenance_history": v1_data.get("maintenance_history", []),
        }

    def get_source_twin_type(self) -> str:
        return "MaintenanceTwin"


BRIDGES: dict[str, TwinDataBridge] = {
    "DesignTwin": DesignTwinBridge(),
    "ManufacturingTwin": ManufacturingTwinBridge(),
    "FlightTwin": FlightTwinBridge(),
    "MaintenanceTwin": MaintenanceTwinBridge(),
}


def get_bridge(twin_type: str) -> TwinDataBridge | None:
    return BRIDGES.get(twin_type)