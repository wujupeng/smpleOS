import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'services', 'aircraft-core-service'))

from src.domain.enums import LifecycleState, LinkType, ObjectType, PropertyType, SourceTag, BaselineType
from src.domain.entities.aircraft_object import AircraftObject
from src.domain.entities.aircraft_object_version import AircraftObjectVersion
from src.domain.entities.property_definition import PropertyDefinition
from src.domain.value_objects.aircraft_object_link import AircraftObjectLink
from src.domain.value_objects.aircraft_property import AircraftProperty
from src.domain.services.property_service import PropertyService


class TestAircraftObject:

    def test_create_object(self):
        obj = AircraftObject(object_type=ObjectType.Component, name="Test Wing")
        obj.generate_id()
        assert obj.id.startswith("AOBJ-CP-")
        assert obj.object_type == ObjectType.Component
        assert obj.lifecycle_state == LifecycleState.Concept

    def test_object_type_hierarchy_valid(self):
        assert AircraftObject.validate_parent_child_type(ObjectType.Aircraft, ObjectType.System)
        assert AircraftObject.validate_parent_child_type(ObjectType.System, ObjectType.Subsystem)
        assert AircraftObject.validate_parent_child_type(ObjectType.Component, ObjectType.Part)

    def test_object_type_hierarchy_invalid(self):
        assert not AircraftObject.validate_parent_child_type(ObjectType.Part, ObjectType.Aircraft)
        assert not AircraftObject.validate_parent_child_type(ObjectType.Part, ObjectType.Part)

    def test_lifecycle_transition_valid(self):
        obj = AircraftObject(object_type=ObjectType.Component, name="Test")
        obj.transition_to(LifecycleState.Design, {"requirement_associations": True})
        assert obj.lifecycle_state == LifecycleState.Design

    def test_lifecycle_transition_invalid(self):
        obj = AircraftObject(object_type=ObjectType.Component, name="Test")
        with pytest.raises(ValueError):
            obj.transition_to(LifecycleState.Operation)

    def test_lifecycle_transition_missing_validation(self):
        obj = AircraftObject(object_type=ObjectType.Component, name="Test")
        with pytest.raises(ValueError):
            obj.transition_to(LifecycleState.Design, {"requirement_associations": False})

    def test_add_property(self):
        obj = AircraftObject(object_type=ObjectType.Component, name="Test")
        obj.generate_id()
        prop = AircraftProperty(
            value_id="v1", object_id=obj.id, property_def_id="pd1",
            value=12.0, unit="m", source=SourceTag.DesignValue,
        )
        obj.add_property(prop)
        assert len(obj.properties) == 1

    def test_optimistic_lock(self):
        obj = AircraftObject(object_type=ObjectType.Component, name="Test")
        assert obj.optimistic_lock_version == 1


class TestAircraftObjectVersion:

    def test_version_creation(self):
        version = AircraftObjectVersion(
            version_id="AVER-test-1",
            object_id="AOBJ-CP-test",
            version_number=1,
            snapshot={"name": "Test"},
            change_summary="Initial creation",
            author="test_user",
        )
        assert version.version_number == 1
        assert version.is_frozen is False
        assert version.baseline_type == BaselineType.None_

    def test_version_freeze(self):
        version = AircraftObjectVersion(
            version_id="AVER-test-1",
            object_id="AOBJ-CP-test",
            version_number=1,
            snapshot={},
            change_summary="Test",
            author="test",
        )
        version.freeze()
        assert version.is_frozen is True

    def test_baseline_type_setting(self):
        version = AircraftObjectVersion(
            version_id="AVER-test-1",
            object_id="AOBJ-CP-test",
            version_number=1,
            snapshot={},
            change_summary="Test",
            author="test",
        )
        version.set_baseline_type(BaselineType.Frozen)
        assert version.baseline_type == BaselineType.Frozen
        assert version.is_frozen is True


class TestAircraftObjectLink:

    def test_link_creation(self):
        link = AircraftObjectLink(
            link_id="l1",
            source_id="AOBJ-AC-001",
            target_id="AOBJ-SY-001",
            link_type=LinkType.Contains,
        )
        assert link.link_type == LinkType.Contains
        assert link.involves("AOBJ-AC-001")
        assert link.get_other("AOBJ-AC-001") == "AOBJ-SY-001"

    def test_link_no_self_reference(self):
        with pytest.raises(Exception):
            AircraftObjectLink(
                link_id="l1",
                source_id="AOBJ-CP-001",
                target_id="AOBJ-CP-001",
                link_type=LinkType.DependsOn,
            )


class TestPropertyDefinition:

    def test_property_definition_creation(self):
        prop_def = PropertyDefinition(
            id="pd1",
            name="Wingspan",
            property_type=PropertyType.Geometric,
            data_type="Float",
            unit="m",
            constraints={"range": {"min": 0}},
        )
        assert prop_def.name == "Wingspan"
        assert prop_def.validate_value(12.0) is True

    def test_property_validation_range(self):
        prop_def = PropertyDefinition(
            id="pd1",
            name="Wingspan",
            property_type=PropertyType.Geometric,
            data_type="Float",
            unit="m",
            constraints={"range": {"min": 0, "max": 100}},
        )
        assert prop_def.validate_value(50.0) is True
        assert prop_def.validate_value(-5.0) is False
        assert prop_def.validate_value(150.0) is False


class TestPropertyService:

    def test_unit_conversion(self):
        result = PropertyService.convert_unit(12.0, "m", "mm")
        assert result == 12000.0

    def test_unit_conversion_reverse(self):
        result = PropertyService.convert_unit(12000.0, "mm", "m")
        assert result == 12.0

    def test_unit_conversion_incompatible(self):
        with pytest.raises(ValueError):
            PropertyService.convert_unit(12.0, "m", "kg")

    def test_unit_conversion_same(self):
        result = PropertyService.convert_unit(12.0, "m", "m")
        assert result == 12.0