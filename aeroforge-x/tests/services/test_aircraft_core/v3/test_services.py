import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "services", "aircraft-core-service"))

from src.domain.services.schema_registry_service import SchemaRegistryService
from src.domain.services.unit_conversion_service import UnitConversionService
from src.domain.services.attribute_name_service import AttributeNameService
from src.domain.services.schema_migration_service import SchemaMigrationService
from src.domain.services.domain_event_publisher import DomainEventPublisher, FieldChange, PropagationHint


class TestSchemaRegistryService:
    def setup_method(self):
        SchemaRegistryService._registry.clear()

    def test_register_schema(self):
        entry = SchemaRegistryService.register_schema(
            schema_name="AircraftGeometry",
            schema_type="AircraftGeometry",
            field_definitions=[{"field_name": "wingspan", "data_type": "float", "is_required": True}],
        )
        assert entry["schema_name"] == "AircraftGeometry"
        assert entry["version"] == 1
        assert entry["status"] == "Draft"

    def test_publish_schema_version(self):
        entry = SchemaRegistryService.register_schema(
            schema_name="AircraftGeometry",
            schema_type="AircraftGeometry",
            field_definitions=[{"field_name": "wingspan", "data_type": "float"}],
        )
        result = SchemaRegistryService.publish_schema_version(entry["schema_id"])
        assert result["version"] == 2
        assert result["status"] == "Published"

    def test_deprecate_schema(self):
        entry = SchemaRegistryService.register_schema(
            schema_name="AircraftGeometry",
            schema_type="AircraftGeometry",
            field_definitions=[{"field_name": "wingspan", "data_type": "float"}],
        )
        result = SchemaRegistryService.deprecate_schema_version(entry["schema_id"])
        assert result["status"] == "Deprecated"

    def test_validate_compatibility_compatible(self):
        old = [{"field_name": "wingspan", "data_type": "float"}]
        new = [{"field_name": "wingspan", "data_type": "float"}, {"field_name": "dihedral", "data_type": "float", "default_value": 0.0}]
        result = SchemaRegistryService.validate_compatibility(old, new)
        assert result["compatible"] is True

    def test_validate_compatibility_breaking(self):
        old = [{"field_name": "wingspan", "data_type": "float"}]
        new = [{"field_name": "wingspan", "data_type": "int"}]
        result = SchemaRegistryService.validate_compatibility(old, new)
        assert result["compatible"] is False

    def test_validate_compatibility_required_no_default(self):
        old = [{"field_name": "wingspan", "data_type": "float"}]
        new = [{"field_name": "wingspan", "data_type": "float"}, {"field_name": "new_field", "data_type": "float", "is_required": True}]
        result = SchemaRegistryService.validate_compatibility(old, new)
        assert result["compatible"] is False

    def test_generate_migration_path(self):
        old = [{"field_name": "wingspan", "data_type": "float"}]
        new = [{"field_name": "wingspan", "data_type": "float"}, {"field_name": "dihedral", "data_type": "float", "default_value": 0.0}]
        path = SchemaRegistryService.generate_migration_path(old, new)
        assert len(path["added"]) == 1
        assert path["added"][0]["field_name"] == "dihedral"

    def test_execute_migration(self):
        entry = SchemaRegistryService.register_schema(
            schema_name="AircraftGeometry",
            schema_type="AircraftGeometry",
            field_definitions=[{"field_name": "wingspan", "data_type": "float"}],
        )
        new_fields = [{"field_name": "wingspan", "data_type": "float"}, {"field_name": "dihedral", "data_type": "float", "default_value": 0.0}]
        SchemaRegistryService.publish_schema_version(entry["schema_id"], new_fields)
        objects = [{"id": "obj1", "wingspan": 35.0}, {"id": "obj2", "wingspan": 40.0}]
        result = SchemaRegistryService.execute_migration(entry["schema_id"], objects)
        assert result["migrated_count"] == 2
        assert result["failed_count"] == 0

    def test_execute_migration_partial_failure(self):
        entry = SchemaRegistryService.register_schema(
            schema_name="AircraftGeometry",
            schema_type="AircraftGeometry",
            field_definitions=[{"field_name": "wingspan", "data_type": "float"}],
        )
        new_fields = [{"field_name": "wingspan", "data_type": "float"}, {"field_name": "dihedral", "data_type": "float", "default_value": 0.0}]
        SchemaRegistryService.publish_schema_version(entry["schema_id"], new_fields)
        objects = [{"id": "obj1", "wingspan": 35.0}]
        result = SchemaRegistryService.execute_migration(entry["schema_id"], objects)
        assert result["migrated_count"] == 1

    def test_validate_cross_schema_ref_valid(self):
        result = SchemaRegistryService.validate_cross_schema_ref("geometry_ref", "AircraftGeometry")
        assert result["valid"] is True

    def test_validate_cross_schema_ref_invalid(self):
        result = SchemaRegistryService.validate_cross_schema_ref("ref", "UnknownSchema")
        assert result["valid"] is False

    def test_list_schemas(self):
        SchemaRegistryService.register_schema("S1", "AircraftGeometry", [])
        SchemaRegistryService.register_schema("S2", "AircraftStructure", [])
        all_schemas = SchemaRegistryService.list_schemas()
        assert len(all_schemas) == 2

    def test_list_schemas_by_type(self):
        SchemaRegistryService.register_schema("S1", "AircraftGeometry", [])
        SchemaRegistryService.register_schema("S2", "AircraftStructure", [])
        geo_schemas = SchemaRegistryService.list_schemas("AircraftGeometry")
        assert len(geo_schemas) == 1


class TestUnitConversionService:
    def test_m_to_ft(self):
        result = UnitConversionService.convert_unit(1.0, "m", "ft")
        assert result == pytest.approx(3.28084, rel=1e-3)

    def test_ft_to_m(self):
        result = UnitConversionService.convert_unit(1.0, "ft", "m")
        assert result == pytest.approx(0.3048, rel=1e-3)

    def test_kg_to_lb(self):
        result = UnitConversionService.convert_unit(1.0, "kg", "lb")
        assert result == pytest.approx(2.20462, rel=1e-3)

    def test_N_to_kN(self):
        assert UnitConversionService.convert_unit(1000.0, "N", "kN") == pytest.approx(1.0, rel=1e-3)

    def test_MPa_to_psi(self):
        result = UnitConversionService.convert_unit(1.0, "MPa", "psi")
        assert result == pytest.approx(145.038, rel=1e-2)

    def test_deg_to_rad(self):
        result = UnitConversionService.convert_unit(180.0, "deg", "rad")
        assert result == pytest.approx(3.14159, rel=1e-3)

    def test_same_unit(self):
        assert UnitConversionService.convert_unit(5.0, "m", "m") == 5.0

    def test_incompatible_units_raises(self):
        with pytest.raises(ValueError, match="Incompatible"):
            UnitConversionService.convert_unit(1.0, "m", "kg")

    def test_validate_dimensional_compatibility_true(self):
        assert UnitConversionService.validate_dimensional_compatibility("m", "ft") is True

    def test_validate_dimensional_compatibility_false(self):
        assert UnitConversionService.validate_dimensional_compatibility("m", "kg") is False

    def test_get_canonical_value(self):
        si_val, si_unit = UnitConversionService.get_canonical_value(1.0, "ft")
        assert si_val == pytest.approx(0.3048, rel=1e-3)
        assert si_unit == "m"

    def test_get_display_value(self):
        result = UnitConversionService.get_display_value(0.3048, "ft")
        assert result == pytest.approx(1.0, rel=1e-3)

    def test_get_supported_units(self):
        units = UnitConversionService.get_supported_units()
        assert "length" in units
        assert "m" in units["length"]

    def test_performance_under_1ms(self):
        start = time.perf_counter()
        for _ in range(1000):
            UnitConversionService.convert_unit(1.0, "m", "ft")
        elapsed = (time.perf_counter() - start) / 1000 * 1000
        assert elapsed < 1.0, f"Unit conversion took {elapsed:.3f}ms per call"


class TestAttributeNameService:
    def setup_method(self):
        AttributeNameService._canonical_names.clear()
        AttributeNameService._alias_map.clear()

    def test_register_canonical_name(self):
        entry = AttributeNameService.register_canonical_name("wingspan", "geometry", "Wing span")
        assert entry["canonical_name"] == "wingspan"
        assert entry["domain"] == "geometry"

    def test_register_duplicate_fails(self):
        AttributeNameService.register_canonical_name("wingspan", "geometry", "Wing span")
        with pytest.raises(ValueError, match="already registered"):
            AttributeNameService.register_canonical_name("wingspan", "geometry", "Wing span")

    def test_add_alias(self):
        AttributeNameService.register_canonical_name("wingspan", "geometry", "Wing span")
        entry = AttributeNameService.add_alias("wingspan", "span")
        assert "span" in entry["aliases"]

    def test_add_alias_conflict_fails(self):
        AttributeNameService.register_canonical_name("wingspan", "geometry", "Wing span")
        AttributeNameService.register_canonical_name("chord_length", "geometry", "Chord")
        AttributeNameService.add_alias("wingspan", "span")
        with pytest.raises(ValueError, match="already mapped"):
            AttributeNameService.add_alias("chord_length", "span")

    def test_resolve_canonical_name(self):
        AttributeNameService.register_canonical_name("wingspan", "geometry", "Wing span")
        result = AttributeNameService.resolve_name("wingspan")
        assert result["canonical_name"] == "wingspan"
        assert result["is_alias"] is False

    def test_resolve_alias(self):
        AttributeNameService.register_canonical_name("wingspan", "geometry", "Wing span")
        AttributeNameService.add_alias("wingspan", "span")
        result = AttributeNameService.resolve_name("span")
        assert result["canonical_name"] == "wingspan"
        assert result["is_alias"] is True

    def test_resolve_unknown(self):
        result = AttributeNameService.resolve_name("unknown_attr")
        assert result.get("unknown") is True

    def test_validate_no_conflict_true(self):
        assert AttributeNameService.validate_no_conflict("new_name") is True

    def test_validate_no_conflict_false(self):
        AttributeNameService.register_canonical_name("wingspan", "geometry", "Wing span")
        assert AttributeNameService.validate_no_conflict("wingspan") is False


class TestSchemaMigrationService:
    def test_infer_schema_type_geometry(self):
        result = SchemaMigrationService.infer_schema_type({"wingspan": 35.0, "chord_length": 3.5, "wing_area": 120.0})
        assert result == "AircraftGeometry"

    def test_infer_schema_type_structure(self):
        result = SchemaMigrationService.infer_schema_type({"material_id": "AL7075", "yield_strength": 503.0, "design_weight": 500.0})
        assert result == "AircraftStructure"

    def test_infer_schema_type_propulsion(self):
        result = SchemaMigrationService.infer_schema_type({"engine_type": "Turbofan", "max_thrust": 120000.0})
        assert result == "AircraftPropulsion"

    def test_infer_schema_type_unknown(self):
        result = SchemaMigrationService.infer_schema_type({"foo": 1.0, "bar": 2.0})
        assert result == "Unknown"

    def test_migrate_dict_to_schema(self):
        result = SchemaMigrationService.migrate_dict_to_schema(
            "AircraftGeometry",
            {"wingspan": 35.0, "chord_length": 3.5, "sweep_angle": 25.0, "taper_ratio": 0.3, "thickness_ratio": 0.12, "wing_area": 120.0},
        )
        assert result["success"] is True
        assert "aspect_ratio" in result.get("derived_params", {})

    def test_apply_alias_mapping(self):
        AttributeNameService._canonical_names.clear()
        AttributeNameService._alias_map.clear()
        AttributeNameService.register_canonical_name("wingspan", "geometry", "Wing span")
        AttributeNameService.add_alias("wingspan", "span")

        result = SchemaMigrationService.apply_alias_mapping({"span": 35.0})
        assert "wingspan" in result
        assert result["wingspan"] == 35.0

    def test_populate_defaults(self):
        result = SchemaMigrationService.populate_defaults("AircraftGeometry", {"wingspan": 35.0})
        assert "dihedral_angle" in result

    def test_extract_extra_fields(self):
        result = SchemaMigrationService.extract_extra_fields(
            "AircraftGeometry",
            {"wingspan": 35.0, "chord_length": 3.5, "sweep_angle": 25.0, "taper_ratio": 0.3, "thickness_ratio": 0.12, "wing_area": 120.0, "custom_field": "value"},
        )
        assert "custom_field" in result

    def test_batch_migrate(self):
        objects = [
            {"wingspan": 35.0, "chord_length": 3.5, "sweep_angle": 25.0, "taper_ratio": 0.3, "thickness_ratio": 0.12, "wing_area": 120.0},
            {"wingspan": 40.0, "chord_length": 4.0, "sweep_angle": 30.0, "taper_ratio": 0.25, "thickness_ratio": 0.1, "wing_area": 150.0},
        ]
        result = SchemaMigrationService.batch_migrate("AircraftGeometry", objects)
        assert result["total"] == 2
        assert result["succeeded"] == 2


class TestDomainEventPublisher:
    def setup_method(self):
        DomainEventPublisher._event_cache.clear()

    def test_publish_object_change_event(self):
        event = DomainEventPublisher.publish_object_change_event(
            aggregate_id="obj-001",
            changed_fields=[FieldChange(field_path="wingspan", old_value=30.0, new_value=35.0, unit="m", schema_type="AircraftGeometry")],
        )
        assert event.event_type == "aeroforge.aircraft.object.updated"
        assert event.aggregate_id == "obj-001"
        assert len(event.changed_fields) == 1

    def test_build_propagation_hints(self):
        hints = DomainEventPublisher.build_propagation_hints([
            FieldChange(field_path="wingspan", old_value=30.0, new_value=35.0, unit="m", schema_type="AircraftGeometry"),
        ])
        assert len(hints) > 0

    def test_event_cached(self):
        DomainEventPublisher.publish_object_change_event(
            aggregate_id="obj-001",
            changed_fields=[FieldChange(field_path="wingspan", old_value=30.0, new_value=35.0, unit="m", schema_type="AircraftGeometry")],
        )
        cached = DomainEventPublisher.get_cached_events()
        assert len(cached) == 1

    def test_clear_cache(self):
        DomainEventPublisher.publish_object_change_event(
            aggregate_id="obj-001",
            changed_fields=[FieldChange(field_path="wingspan", old_value=30.0, new_value=35.0, unit="m", schema_type="AircraftGeometry")],
        )
        DomainEventPublisher.clear_cache()
        assert len(DomainEventPublisher.get_cached_events()) == 0

    def test_custom_event_type(self):
        event = DomainEventPublisher.publish_object_change_event(
            aggregate_id="obj-001",
            changed_fields=[],
            event_type="aeroforge.twin.anomaly.detected",
        )
        assert event.event_type == "aeroforge.twin.anomaly.detected"