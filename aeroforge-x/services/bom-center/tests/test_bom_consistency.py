from __future__ import annotations

import pytest

from src.domain.entities.bom_item import BOMItem, EBOM, MBOM, SBOM
from src.domain.services.bom_consistency_checker import (
    BOMConsistencyChecker,
    DiffType,
    SyncSuggestion,
)


@pytest.fixture
def sample_ebom() -> EBOM:
    ebom = EBOM(spec_id="SPEC-CON-001")
    aircraft = BOMItem(item_code="AAF-AC-CON", name="飞行器", bom_type="ebom", part_type="assembly")
    aircraft.add_child(BOMItem(item_code="AAF-SPAR-CON", name="翼梁", part_type="structural"))
    aircraft.add_child(BOMItem(item_code="AAF-RIB-CON", name="肋板", part_type="structural", quantity=8))
    aircraft.add_child(BOMItem(item_code="AAF-SKIN-CON", name="蒙皮", part_type="skin"))
    ebom.set_root(aircraft)
    ebom.publish()
    return ebom


@pytest.fixture
def checker():
    return BOMConsistencyChecker()


class TestCheckConsistency:
    def test_consistent_boms(self, sample_ebom, checker):
        from src.domain.services.mbom_transform_domain_service import MBOMTransformDomainService
        from src.domain.services.sbom_gen_domain_service import SBOMGenerator

        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform_from_ebom(sample_ebom)

        sbom_gen = SBOMGenerator()
        sbom = sbom_gen.generate_from_ebom(sample_ebom, mbom)

        report = checker.check_consistency(sample_ebom, mbom, sbom)
        assert isinstance(report.is_consistent, bool)
        assert report.ebom_item_count > 0
        assert report.mbom_item_count > 0
        assert report.sbom_item_count > 0

    def test_ebom_only_consistency(self, sample_ebom, checker):
        report = checker.check_consistency(sample_ebom)
        assert report.ebom_item_count > 0
        assert report.mbom_item_count == 0

    def test_empty_ebom_consistency(self, checker):
        ebom = EBOM(spec_id="SPEC-EMPTY")
        report = checker.check_consistency(ebom)
        assert report.is_consistent is False
        assert len(report.errors) > 0

    def test_mapping_completeness(self, sample_ebom, checker):
        from src.domain.services.mbom_transform_domain_service import MBOMTransformDomainService

        mbom_service = MBOMTransformDomainService()
        mbom = mbom_service.transform_from_ebom(sample_ebom)

        report = checker.check_consistency(sample_ebom, mbom)
        assert "ebom_to_mbom" in report.mapping_completeness
        mc = report.mapping_completeness["ebom_to_mbom"]
        assert mc["total_ebom_items"] > 0
        assert mc["completeness_percent"] >= 0


class TestDetectDifferences:
    def test_no_diffs_when_consistent(self, sample_ebom, checker):
        diffs = checker.detect_differences(sample_ebom)
        assert len(diffs) == 0

    def test_unmapped_ebom_items(self, sample_ebom, checker):
        mbom = MBOM(ebom_id=sample_ebom.id)
        root = BOMItem(item_code="MBOM-ROOT", name="mBOM Root", bom_type="mbom", part_type="assembly")
        root.add_child(BOMItem(
            item_code="MBOM-PART", name="Part", bom_type="mbom", part_type="part",
            ebom_item_code="AAF-SPAR-CON",
        ))
        mbom.set_root(root)

        diffs = checker.detect_differences(sample_ebom, mbom)
        unmapped = [d for d in diffs if d.diff_type == DiffType.UNMAPPED]
        assert len(unmapped) > 0

    def test_added_items_in_sbom(self, sample_ebom, checker):
        mbom = MBOM(ebom_id=sample_ebom.id)
        mbom_root = BOMItem(item_code="MBOM-ROOT", name="mBOM Root", bom_type="mbom", part_type="assembly")
        mbom_root.add_child(BOMItem(item_code="MBOM-P1", name="Part1", bom_type="mbom", part_type="part"))
        mbom.set_root(mbom_root)

        sbom = SBOM(ebom_id=sample_ebom.id, mbom_id=mbom.id)
        sbom_root = BOMItem(item_code="SBOM-ROOT", name="sBOM Root", bom_type="sbom", part_type="assembly")
        sbom_root.add_child(BOMItem(item_code="MBOM-P1", name="Part1", bom_type="sbom", part_type="part"))
        sbom_root.add_child(BOMItem(item_code="SBOM-EXTRA", name="Extra", bom_type="sbom", part_type="part"))
        sbom.set_root(sbom_root)

        diffs = checker.detect_differences(sample_ebom, mbom, sbom)
        added = [d for d in diffs if d.diff_type == DiffType.ADDED]
        assert len(added) > 0


class TestSuggestSync:
    def test_auto_vs_manual_suggestions(self, checker):
        from src.domain.services.bom_consistency_checker import DiffItem

        diffs = [
            DiffItem("C1", "Part1", DiffType.REMOVED, "mbom", "sbom", suggestion=SyncSuggestion.AUTO_SYNC),
            DiffItem("C2", "Part2", DiffType.UNMAPPED, "ebom", "mbom", suggestion=SyncSuggestion.MANUAL_CONFIRM),
            DiffItem("C3", "Part3", DiffType.ADDED, "sbom", "mbom", suggestion=SyncSuggestion.MANUAL_CONFIRM),
        ]

        result = checker.suggest_sync(diffs)
        assert result["total_diffs"] == 3
        assert result["auto_sync_count"] == 1
        assert result["manual_confirm_count"] == 2

    def test_empty_diffs(self, checker):
        result = checker.suggest_sync([])
        assert result["total_diffs"] == 0
        assert result["auto_sync_count"] == 0


class TestAttributeConsistency:
    def test_attribute_mismatch_detected(self, sample_ebom, checker):
        mbom = MBOM(ebom_id=sample_ebom.id)
        root = BOMItem(item_code="MBOM-ROOT", name="mBOM Root", bom_type="mbom", part_type="assembly")
        root.add_child(BOMItem(
            item_code="MBOM-SPAR", name="翼梁(修改)", bom_type="mbom", part_type="structural",
            quantity=2, ebom_item_code="AAF-SPAR-CON",
        ))
        mbom.set_root(root)

        report = checker.check_consistency(sample_ebom, mbom)
        assert report.attribute_consistency["inconsistency_count"] > 0