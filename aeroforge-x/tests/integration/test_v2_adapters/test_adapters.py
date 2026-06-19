import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'services', 'aircraft-core-service'))

from src.infrastructure.adapters.aircraft_object_adapter import (
    AdapterRegistry, DesignCenterAdapter, ManufacturingCenterAdapter,
    OperationCenterAdapter, CertificationCenterAdapter,
)


class TestAircraftObjectAdapter:

    def test_design_center_adapter_to(self):
        adapter = DesignCenterAdapter()
        obj = adapter.to_aircraft_object({
            "id": "DM-001",
            "name": "Wing Design",
            "object_type": "Component",
            "design_data": {"wingspan": 12.0},
        })
        assert obj.name == "Wing Design"
        assert obj.design_data.get("wingspan") == 12.0

    def test_design_center_adapter_from(self):
        adapter = DesignCenterAdapter()
        from src.domain.entities.aircraft_object import AircraftObject
        from src.domain.enums import ObjectType
        obj = AircraftObject(object_type=ObjectType.Component, name="Wing", design_data={"wingspan": 12.0})
        result = adapter.from_aircraft_object(obj)
        assert result["name"] == "Wing"
        assert result["design_data"]["wingspan"] == 12.0

    def test_manufacturing_center_adapter(self):
        adapter = ManufacturingCenterAdapter()
        obj = adapter.to_aircraft_object({
            "id": "WO-001",
            "name": "Wing WO",
            "manufacturing_data": {"actual_wingspan": 12.01},
        })
        assert obj.manufacturing_data.get("actual_wingspan") == 12.01

    def test_adapter_registry(self):
        adapter = AdapterRegistry.get_adapter("DesignModel")
        assert adapter is not None
        assert adapter.get_supported_entity_type() == "DesignModel"

    def test_adapter_registry_all(self):
        all_adapters = AdapterRegistry.get_all_adapters()
        assert "DesignModel" in all_adapters
        assert "WorkOrder" in all_adapters
        assert "FlightData" in all_adapters
        assert "ComplianceItem" in all_adapters
