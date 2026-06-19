import pytest

from services.plm_center.src.domain.entities.product_tree import ProductNode, ProductTree
from services.plm_center.src.domain.services.product_structure_service import ProductStructureService
from services.plm_center.src.domain.services.version_domain_service import Version, VersionDomainService
from services.bom_center.src.domain.entities.bom_item import BOMItem, EBOM
from services.bom_center.src.domain.services.ebom_engine import EBOMEngine


class TestProductTree:
    def test_create_tree_with_root(self) -> None:
        tree = ProductTree(name="Test Aircraft", spec_id="spec-1", created_by="user-1")
        root = ProductNode(part_id="aircraft-1", name="飞行器总装", part_type="assembly")
        tree.set_root(root)
        assert tree.root_node is not None
        assert tree.root_node.part_id == "aircraft-1"

    def test_add_part_to_tree(self) -> None:
        tree = ProductTree(name="Test Aircraft", created_by="user-1")
        root = ProductNode(part_id="aircraft-1", name="飞行器总装")
        tree.set_root(root)
        wing = ProductNode(part_id="wing-1", name="机翼组件", quantity=1)
        result = tree.add_part("aircraft-1", wing)
        assert result is True
        assert len(tree.root_node.children) == 1

    def test_remove_part(self) -> None:
        tree = ProductTree(name="Test Aircraft", created_by="user-1")
        root = ProductNode(part_id="aircraft-1", name="飞行器总装")
        tree.set_root(root)
        wing = ProductNode(part_id="wing-1", name="机翼组件")
        tree.add_part("aircraft-1", wing)
        result = tree.remove_part("wing-1")
        assert result is True
        assert len(tree.root_node.children) == 0

    def test_where_used(self) -> None:
        tree = ProductTree(name="Test Aircraft", created_by="user-1")
        root = ProductNode(part_id="aircraft-1", name="飞行器总装")
        tree.set_root(root)
        wing = ProductNode(part_id="wing-1", name="机翼组件")
        tree.add_part("aircraft-1", wing)
        spar = ProductNode(part_id="spar-1", name="翼梁")
        wing.add_child(spar)
        result = tree.where_used("spar-1")
        assert "wing-1" in result or "aircraft-1" in result

    def test_to_dict(self) -> None:
        tree = ProductTree(name="Test", created_by="user-1")
        root = ProductNode(part_id="root-1", name="Root")
        tree.set_root(root)
        d = tree.to_dict()
        assert d["root_node"]["part_id"] == "root-1"


class TestVersionDomainService:
    def test_create_minor_version(self) -> None:
        service = VersionDomainService()
        v = service.create_version("obj-1", "小修改", "user-1", {"key": "val"}, 1, 0)
        assert v.major == 1
        assert v.minor == 1

    def test_create_major_version(self) -> None:
        service = VersionDomainService()
        v = service.create_version("obj-1", "重大变更", "user-1", {"key": "val"}, 1, 2)
        assert v.major == 2
        assert v.minor == 0

    def test_compare_versions(self) -> None:
        service = VersionDomainService()
        v1 = Version(object_id="obj-1", major=1, minor=0, snapshot={"a": 1, "b": 2})
        v2 = Version(object_id="obj-1", major=1, minor=1, snapshot={"a": 1, "b": 3, "c": 4})
        diff = service.compare_versions(v1, v2)
        assert "b" in diff["changed"]
        assert "c" in diff["added"]


class TestEBOMEngine:
    def test_generate_ebom_from_model(self) -> None:
        engine = EBOMEngine()
        model_data = {
            "assembly": {
                "components": {
                    "fuselage": {"parameters": {"length_m": 8, "diameter_m": 1.2}},
                    "wing": {"parameters": {"wingspan_m": 15, "aspect_ratio": 12, "wing_area_m2": 18.75}},
                    "tail": {"parameters": {"h_tail_area_m2": 2.5, "v_tail_area_m2": 1.5}},
                },
            },
        }
        ebom = engine.generate_from_model(spec_id="spec-1", model_data=model_data)
        assert ebom.root_item is not None
        assert ebom.root_item.name == "飞行器总装"
        assert len(ebom.root_item.children) == 3

    def test_ebom_has_sub_parts(self) -> None:
        engine = EBOMEngine()
        model_data = {
            "assembly": {
                "components": {
                    "wing": {"parameters": {"wingspan_m": 15}},
                },
            },
        }
        ebom = engine.generate_from_model(spec_id="spec-1", model_data=model_data)
        wing = ebom.root_item.children[0] if ebom.root_item else None
        assert wing is not None
        assert len(wing.children) > 0

    def test_ebom_publish(self) -> None:
        engine = EBOMEngine()
        model_data = {"assembly": {"components": {"wing": {"parameters": {"wingspan_m": 15}}}}}
        ebom = engine.generate_from_model(spec_id="spec-1", model_data=model_data)
        ebom.publish()
        assert ebom.status == "published"
        assert len(ebom.domain_events) == 1
        assert ebom.domain_events[0].event_type == "ebom.generated"