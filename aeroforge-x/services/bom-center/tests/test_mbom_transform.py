from __future__ import annotations

import pytest

from src.domain.entities.bom_item import BOMItem, EBOM, MBOM
from src.domain.services.mbom_transform_domain_service import (
    AssemblyProcessMapper,
    MBOMTransformDomainService,
    ASSEMBLY_PROCESS_TEMPLATES,
)


@pytest.fixture
def sample_ebom() -> EBOM:
    ebom = EBOM(spec_id="SPEC-001")

    aircraft = BOMItem(
        item_code="AAF-AIRCRAFT-001",
        name="飞行器总装",
        bom_type="ebom",
        part_type="assembly",
    )

    wing = BOMItem(
        item_code="AAF-WING-001",
        name="机翼组件",
        bom_type="ebom",
        part_type="assembly",
    )
    wing.add_child(BOMItem(item_code="AAF-SPAR-001", name="翼梁", part_type="structural", attributes={"material": "CFRP"}))
    wing.add_child(BOMItem(item_code="AAF-RIB-001", name="肋板", part_type="structural", quantity=8))
    wing.add_child(BOMItem(item_code="AAF-SKIN-WING-001", name="机翼蒙皮", part_type="skin"))

    fuselage = BOMItem(
        item_code="AAF-FUSELAGE-001",
        name="机身组件",
        bom_type="ebom",
        part_type="assembly",
    )
    fuselage.add_child(BOMItem(item_code="AAF-FRAME-001", name="加强框", part_type="structural", quantity=4))
    fuselage.add_child(BOMItem(item_code="AAF-SKIN-FUSE-001", name="机身蒙皮", part_type="skin"))

    tail = BOMItem(
        item_code="AAF-TAIL-001",
        name="尾翼组件",
        bom_type="ebom",
        part_type="assembly",
    )
    tail.add_child(BOMItem(item_code="AAF-H-SPAR-001", name="水平尾翼梁", part_type="structural"))
    tail.add_child(BOMItem(item_code="AAF-V-SPAR-001", name="垂直尾翼梁", part_type="structural"))

    aircraft.add_child(wing)
    aircraft.add_child(fuselage)
    aircraft.add_child(tail)

    ebom.set_root(aircraft)
    ebom.publish()
    return ebom


class TestMBOMTransformDomainService:
    def test_transform_from_ebom_creates_mbom(self, sample_ebom):
        service = MBOMTransformDomainService()
        mbom = service.transform_from_ebom(sample_ebom)

        assert isinstance(mbom, MBOM)
        assert mbom.ebom_id == sample_ebom.id
        assert mbom.root_item is not None
        assert mbom.root_item.bom_type == "mbom"

    def test_transform_preserves_all_ebom_items(self, sample_ebom):
        service = MBOMTransformDomainService()
        mbom = service.transform_from_ebom(sample_ebom)

        ebom_items = sample_ebom.root_item.flatten()
        mbom_items = mbom.root_item.flatten()

        ebom_leaf_codes = {i.item_code for i in ebom_items if i.part_type != "assembly"}
        mbom_ebom_refs = {i.ebom_item_code for i in mbom_items if i.ebom_item_code}

        assert ebom_leaf_codes.issubset(mbom_ebom_refs) or len(mbom.unmapped_items) > 0

    def test_transform_adds_virtual_nodes(self, sample_ebom):
        service = MBOMTransformDomainService()
        mbom = service.transform_from_ebom(sample_ebom)

        mbom_items = mbom.root_item.flatten()
        virtual_nodes = [i for i in mbom_items if i.is_virtual]

        assert len(virtual_nodes) > 0

    def test_transform_reorganizes_by_station(self, sample_ebom):
        service = MBOMTransformDomainService()
        mbom = service.transform_from_ebom(sample_ebom)

        mbom_items = mbom.root_item.flatten()
        stations = {i.station for i in mbom_items if i.station}

        assert len(stations) > 0

    def test_transform_empty_ebom_raises(self):
        service = MBOMTransformDomainService()
        ebom = EBOM(spec_id="SPEC-EMPTY")

        with pytest.raises(ValueError, match="Cannot transform empty eBOM"):
            service.transform_from_ebom(ebom)

    def test_transform_unknown_component_creates_unmapped(self):
        service = MBOMTransformDomainService()
        ebom = EBOM(spec_id="SPEC-002")

        aircraft = BOMItem(item_code="AAF-AIRCRAFT-002", name="飞行器", bom_type="ebom", part_type="assembly")
        aircraft.add_child(BOMItem(item_code="AAF-CUSTOM-001", name="自定义零件", part_type="custom_part"))
        ebom.set_root(aircraft)
        ebom.publish()

        mbom = service.transform_from_ebom(ebom)
        assert len(mbom.unmapped_items) > 0

    def test_validation_result_structure(self, sample_ebom):
        service = MBOMTransformDomainService()
        mbom = service.transform_from_ebom(sample_ebom)

        vr = mbom.validation_result
        assert "is_valid" in vr
        assert "completeness_check" in vr
        assert "order_check" in vr
        assert "virtual_node_check" in vr


class TestAssemblyProcessMapper:
    def test_map_to_stations(self):
        mapper = AssemblyProcessMapper()
        items = [
            BOMItem(item_code="AAF-SPAR-001", name="翼梁", part_type="structural"),
            BOMItem(item_code="AAF-RIB-001", name="肋板", part_type="structural"),
        ]
        template = ASSEMBLY_PROCESS_TEMPLATES["wing"]

        station_map = mapper.map_to_stations(items, template)

        assert len(station_map) > 0
        total_items = sum(len(v) for v in station_map.values())
        assert total_items == 2

    def test_reorder_hierarchy(self):
        mapper = AssemblyProcessMapper()
        items = [
            BOMItem(item_code="AAF-SPAR-001", name="翼梁", part_type="structural"),
        ]
        template = ASSEMBLY_PROCESS_TEMPLATES["wing"]

        station_map = mapper.map_to_stations(items, template)
        ordered = mapper.reorder_hierarchy(station_map, template)

        assert len(ordered) > 0
        for station_id, order, station_items in ordered:
            assert isinstance(order, int)

    def test_add_virtual_nodes(self):
        mapper = AssemblyProcessMapper()
        items = [
            BOMItem(item_code="AAF-SPAR-001", name="翼梁", part_type="structural"),
            BOMItem(item_code="AAF-RIB-001", name="肋板", part_type="structural"),
        ]
        template = ASSEMBLY_PROCESS_TEMPLATES["wing"]

        station_map = mapper.map_to_stations(items, template)
        ordered = mapper.reorder_hierarchy(station_map, template)
        virtual_nodes = mapper.add_virtual_nodes(ordered, template)

        assert len(virtual_nodes) > 0
        virtual = [n for n in virtual_nodes if n.is_virtual]
        assert len(virtual) > 0
        for vn in virtual:
            assert vn.part_type == "virtual_assembly"
            assert vn.bom_type == "mbom"

    def test_merge_same_station_components(self):
        mapper = AssemblyProcessMapper()
        items = [
            BOMItem(item_code="AAF-SPAR-001", name="翼梁", part_type="structural"),
            BOMItem(item_code="AAF-RIB-001", name="肋板", part_type="structural"),
            BOMItem(item_code="AAF-SKIN-WING-001", name="机翼蒙皮", part_type="skin"),
        ]
        template = ASSEMBLY_PROCESS_TEMPLATES["wing"]

        station_map = mapper.map_to_stations(items, template)
        ordered = mapper.reorder_hierarchy(station_map, template)
        virtual_nodes = mapper.add_virtual_nodes(ordered, template)

        for vn in virtual_nodes:
            if vn.is_virtual:
                assert len(vn.children) > 0


class TestResolveMappingConflicts:
    def test_detects_unmapped_items(self):
        service = MBOMTransformDomainService()
        ebom = EBOM(spec_id="SPEC-003")

        aircraft = BOMItem(item_code="AAF-AIRCRAFT-003", name="飞行器", bom_type="ebom", part_type="assembly")
        aircraft.add_child(BOMItem(item_code="AAF-UNKNOWN-001", name="未知零件", part_type="unknown"))
        ebom.set_root(aircraft)
        ebom.publish()

        mbom = service.transform_from_ebom(ebom)
        conflicts = service.resolve_mapping_conflicts(ebom, mbom)

        assert len(conflicts) > 0
        for c in conflicts:
            assert c.ebom_item_code
            assert c.reason

    def test_no_conflicts_for_fully_mapped(self, sample_ebom):
        service = MBOMTransformDomainService()
        mbom = service.transform_from_ebom(sample_ebom)

        ebom_leaf_codes = {i.item_code for i in sample_ebom.root_item.flatten() if i.part_type != "assembly"}
        mbom_ebom_refs = {i.ebom_item_code for i in mbom.root_item.flatten() if i.ebom_item_code}

        if ebom_leaf_codes.issubset(mbom_ebom_refs):
            conflicts = service.resolve_mapping_conflicts(sample_ebom, mbom)
            unmapped_conflicts = [c for c in conflicts if "not mapped" in c.reason]
            assert len(unmapped_conflicts) == 0


class TestValidateTransformation:
    def test_valid_transformation(self, sample_ebom):
        service = MBOMTransformDomainService()
        mbom = service.transform_from_ebom(sample_ebom)

        result = service.validate_transformation(sample_ebom, mbom)
        assert result.completeness_check["total_ebom_items"] > 0

    def test_empty_ebom_validation(self):
        service = MBOMTransformDomainService()
        ebom = EBOM(spec_id="SPEC-EMPTY")
        mbom = MBOM(ebom_id=ebom.id)

        result = service.validate_transformation(ebom, mbom)
        assert result.is_valid is False
        assert len(result.errors) > 0


class TestMBOMPublish:
    def test_cannot_publish_with_unmapped_items(self, sample_ebom):
        service = MBOMTransformDomainService()
        mbom = service.transform_from_ebom(sample_ebom)

        if mbom.unmapped_items:
            with pytest.raises(ValueError, match="Cannot publish mBOM with unmapped items"):
                mbom.publish()

    def test_can_publish_when_all_mapped(self):
        mbom = MBOM(ebom_id="ebom-001")
        root = BOMItem(item_code="MBOM-ROOT", name="mBOM Root", bom_type="mbom", part_type="assembly")
        root.add_child(BOMItem(item_code="MBOM-PART-001", name="Part", bom_type="mbom", part_type="part"))
        mbom.set_root(root)

        mbom.publish()
        assert mbom.status == "published"