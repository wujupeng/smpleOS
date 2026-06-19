from __future__ import annotations

import pytest

from src.domain.entities.bom_item import BOMItem, EBOM, MBOM, SBOM
from src.domain.services.sbom_gen_domain_service import SBOMGenerator, SparePartCategory, MaintenanceStrategy


@pytest.fixture
def sample_ebom() -> EBOM:
    ebom = EBOM(spec_id="SPEC-SBOM-001")

    aircraft = BOMItem(item_code="AAF-AIRCRAFT-S1", name="飞行器总装", bom_type="ebom", part_type="assembly")

    wing = BOMItem(item_code="AAF-WING-S1", name="机翼组件", bom_type="ebom", part_type="assembly")
    wing.add_child(BOMItem(item_code="AAF-SPAR-S1", name="翼梁", part_type="structural", attributes={"material": "CFRP"}))
    wing.add_child(BOMItem(item_code="AAF-RIB-S1", name="肋板", part_type="structural", quantity=8))
    wing.add_child(BOMItem(item_code="AAF-SKIN-WING-S1", name="机翼蒙皮", part_type="skin"))

    fuselage = BOMItem(item_code="AAF-FUSE-S1", name="机身组件", bom_type="ebom", part_type="assembly")
    fuselage.add_child(BOMItem(item_code="AAF-FRAME-S1", name="加强框", part_type="structural", quantity=4))
    fuselage.add_child(BOMItem(item_code="AAF-SKIN-FUSE-S1", name="机身蒙皮", part_type="skin"))

    aircraft.add_child(wing)
    aircraft.add_child(fuselage)

    ebom.set_root(aircraft)
    ebom.publish()
    return ebom


class TestSBOMGenerator:
    def test_generate_from_ebom(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        assert isinstance(sbom, SBOM)
        assert sbom.ebom_id == sample_ebom.id
        assert sbom.root_item is not None
        assert sbom.root_item.bom_type == "sbom"

    def test_generate_preserves_all_items(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        ebom_items = sample_ebom.root_item.flatten()
        sbom_items = sbom.root_item.flatten()

        assert len(ebom_items) == len(sbom_items)

    def test_generate_with_mbom_source(self, sample_ebom):
        from src.domain.services.mbom_transform_domain_service import MBOMTransformDomainService

        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform_from_ebom(sample_ebom)

        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom, mbom=mbom)

        assert sbom.mbom_id == mbom.id
        assert sbom.root_item is not None

    def test_generate_empty_ebom_raises(self):
        generator = SBOMGenerator()
        ebom = EBOM(spec_id="SPEC-EMPTY")

        with pytest.raises(ValueError, match="Cannot generate sBOM from empty eBOM"):
            generator.generate_from_ebom(ebom)


class TestApplyMaintenanceStrategy:
    def test_maintenance_strategy_assigned(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        all_items = sbom.root_item.flatten()
        non_virtual = [i for i in all_items if not i.is_virtual]

        for item in non_virtual:
            assert "maintenance_strategy" in item.attributes
            assert "inspection_interval_fh" in item.attributes
            assert "accessibility" in item.attributes

    def test_structural_parts_scheduled_replacement(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        all_items = sbom.root_item.flatten()
        structural = [i for i in all_items if i.part_type == "structural"]

        for item in structural:
            assert item.attributes["maintenance_strategy"] == MaintenanceStrategy.SCHEDULED_REPLACEMENT.value

    def test_skin_parts_condition_based(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        all_items = sbom.root_item.flatten()
        skin_items = [i for i in all_items if i.part_type == "skin"]

        for item in skin_items:
            assert item.attributes["maintenance_strategy"] == MaintenanceStrategy.CONDITION_BASED.value

    def test_environment_adjustment(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom, environment="corrosive")

        all_items = sbom.root_item.flatten()
        for item in all_items:
            if not item.is_virtual and "adjusted_inspection_interval_fh" in item.attributes:
                base = item.attributes.get("inspection_interval_fh", 0)
                adjusted = item.attributes["adjusted_inspection_interval_fh"]
                if base > 0:
                    assert adjusted <= base


class TestMarkSpareParts:
    def test_spare_part_category_assigned(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        all_items = sbom.root_item.flatten()
        non_virtual = [i for i in all_items if not i.is_virtual]

        for item in non_virtual:
            assert "spare_part_category" in item.attributes
            assert item.attributes["spare_part_category"] in [
                SparePartCategory.ESSENTIAL.value,
                SparePartCategory.RECOMMENDED.value,
                SparePartCategory.OPTIONAL.value,
            ]

    def test_structural_parts_are_essential(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        all_items = sbom.root_item.flatten()
        structural = [i for i in all_items if i.part_type == "structural"]

        for item in structural:
            assert item.attributes["spare_part_category"] == SparePartCategory.ESSENTIAL.value
            assert item.attributes.get("safety_critical") is True

    def test_procurement_lead_time_assigned(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        all_items = sbom.root_item.flatten()
        non_virtual = [i for i in all_items if not i.is_virtual]

        for item in non_virtual:
            assert "procurement_lead_time_days" in item.attributes
            assert item.attributes["procurement_lead_time_days"] >= 0


class TestAssignReplacementCycle:
    def test_replacement_cycle_assigned(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        all_items = sbom.root_item.flatten()
        for item in all_items:
            assert "replacement_cycle_fh" in item.attributes

    def test_material_fatigue_factor(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        all_items = sbom.root_item.flatten()
        cfrp_items = [i for i in all_items if i.attributes.get("material") == "CFRP"]

        for item in cfrp_items:
            assert item.attributes["material_fatigue_factor"] == 1.2

    def test_environment_factor_corrosive(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom, environment="corrosive")

        all_items = sbom.root_item.flatten()
        non_virtual = [i for i in all_items if not i.is_virtual]

        for item in non_virtual:
            assert item.attributes.get("environment_factor") == 0.8

    def test_virtual_nodes_zero_cycle(self, sample_ebom):
        from src.domain.services.mbom_transform_domain_service import MBOMTransformDomainService

        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform_from_ebom(sample_ebom)

        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom, mbom=mbom)

        all_items = sbom.root_item.flatten()
        virtual = [i for i in all_items if i.is_virtual]

        for item in virtual:
            assert item.attributes["replacement_cycle_fh"] == 0


class TestSBOMPublish:
    def test_publish_sbom(self, sample_ebom):
        generator = SBOMGenerator()
        sbom = generator.generate_from_ebom(sample_ebom)

        sbom.publish()
        assert sbom.status == "published"

    def test_cannot_publish_empty_sbom(self):
        sbom = SBOM(ebom_id="ebom-001")

        with pytest.raises(ValueError, match="Cannot publish empty sBOM"):
            sbom.publish()