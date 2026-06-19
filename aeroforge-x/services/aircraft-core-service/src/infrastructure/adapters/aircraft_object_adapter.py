from abc import ABC, abstractmethod
from typing import Any

from src.domain.entities.aircraft_object import AircraftObject


class AircraftObjectAdapter(ABC):

    @abstractmethod
    def to_aircraft_object(self, entity: Any) -> AircraftObject:
        pass

    @abstractmethod
    def from_aircraft_object(self, obj: AircraftObject) -> Any:
        pass

    @abstractmethod
    def get_supported_entity_type(self) -> str:
        pass


class DesignCenterAdapter(AircraftObjectAdapter):

    def to_aircraft_object(self, entity: Any) -> AircraftObject:
        data = entity if isinstance(entity, dict) else {}
        return AircraftObject(
            id=data.get("id", ""),
            object_type=data.get("object_type", "Component"),
            name=data.get("name", ""),
            lifecycle_state=data.get("lifecycle_state", "Design"),
            design_data=data.get("design_data", {}),
        )

    def from_aircraft_object(self, obj: AircraftObject) -> dict:
        return {
            "id": obj.id,
            "name": obj.name,
            "design_data": obj.design_data,
        }

    def get_supported_entity_type(self) -> str:
        return "DesignModel"


class ManufacturingCenterAdapter(AircraftObjectAdapter):

    def to_aircraft_object(self, entity: Any) -> AircraftObject:
        data = entity if isinstance(entity, dict) else {}
        return AircraftObject(
            id=data.get("id", ""),
            object_type=data.get("object_type", "Component"),
            name=data.get("name", ""),
            lifecycle_state=data.get("lifecycle_state", "Manufacturing"),
            manufacturing_data=data.get("manufacturing_data", {}),
        )

    def from_aircraft_object(self, obj: AircraftObject) -> dict:
        return {
            "id": obj.id,
            "name": obj.name,
            "manufacturing_data": obj.manufacturing_data,
        }

    def get_supported_entity_type(self) -> str:
        return "WorkOrder"


class OperationCenterAdapter(AircraftObjectAdapter):

    def to_aircraft_object(self, entity: Any) -> AircraftObject:
        data = entity if isinstance(entity, dict) else {}
        return AircraftObject(
            id=data.get("id", ""),
            object_type=data.get("object_type", "Aircraft"),
            name=data.get("name", ""),
            lifecycle_state=data.get("lifecycle_state", "Operation"),
            operation_data=data.get("operation_data", {}),
        )

    def from_aircraft_object(self, obj: AircraftObject) -> dict:
        return {
            "id": obj.id,
            "name": obj.name,
            "operation_data": obj.operation_data,
        }

    def get_supported_entity_type(self) -> str:
        return "FlightData"


class CertificationCenterAdapter(AircraftObjectAdapter):

    def to_aircraft_object(self, entity: Any) -> AircraftObject:
        data = entity if isinstance(entity, dict) else {}
        return AircraftObject(
            id=data.get("id", ""),
            object_type=data.get("object_type", "Component"),
            name=data.get("name", ""),
            lifecycle_state=data.get("lifecycle_state", "Test"),
            certification_data=data.get("certification_data", {}),
        )

    def from_aircraft_object(self, obj: AircraftObject) -> dict:
        return {
            "id": obj.id,
            "name": obj.name,
            "certification_data": obj.certification_data,
        }

    def get_supported_entity_type(self) -> str:
        return "ComplianceItem"


class RequirementCenterAdapter(AircraftObjectAdapter):

    def to_aircraft_object(self, entity: Any) -> AircraftObject:
        data = entity if isinstance(entity, dict) else {}
        return AircraftObject(
            id=data.get("id", ""),
            object_type=data.get("object_type", "System"),
            name=data.get("name", ""),
            lifecycle_state=data.get("lifecycle_state", "Concept"),
        )

    def from_aircraft_object(self, obj: AircraftObject) -> dict:
        return {"id": obj.id, "name": obj.name}

    def get_supported_entity_type(self) -> str:
        return "Requirement"


class KnowledgeCenterAdapter(AircraftObjectAdapter):

    def to_aircraft_object(self, entity: Any) -> AircraftObject:
        data = entity if isinstance(entity, dict) else {}
        return AircraftObject(
            id=data.get("id", ""),
            object_type=data.get("object_type", "Component"),
            name=data.get("name", ""),
        )

    def from_aircraft_object(self, obj: AircraftObject) -> dict:
        return {"id": obj.id, "name": obj.name}

    def get_supported_entity_type(self) -> str:
        return "KnowledgeNode"


class AdapterRegistry:
    _adapters: dict[str, AircraftObjectAdapter] = {}

    @classmethod
    def register(cls, adapter: AircraftObjectAdapter) -> None:
        cls._adapters[adapter.get_supported_entity_type()] = adapter

    @classmethod
    def get_adapter(cls, entity_type: str) -> AircraftObjectAdapter | None:
        return cls._adapters.get(entity_type)

    @classmethod
    def get_all_adapters(cls) -> dict[str, AircraftObjectAdapter]:
        return cls._adapters.copy()


AdapterRegistry.register(DesignCenterAdapter())
AdapterRegistry.register(ManufacturingCenterAdapter())
AdapterRegistry.register(OperationCenterAdapter())
AdapterRegistry.register(CertificationCenterAdapter())
AdapterRegistry.register(RequirementCenterAdapter())
AdapterRegistry.register(KnowledgeCenterAdapter())