"""AeroForge-X V6.0/V6.1 Unit Tests - RegulatoryLibraryService
REQ-CERT-008~013, REQ-VP-020
"""

import pytest

from src.domain.services.certification.regulatory_library_service import (
    RegulatoryLibraryService,
    RegulationType,
    RegulationSection,
    RegulatoryLibrary,
    RequirementMapping,
    RegulationUpdateResult,
)


@pytest.fixture
def service():
    return RegulatoryLibraryService()


class TestImportRegulation:

    def test_import_faa_part_23(self, service):
        lib = service.importRegulation(RegulationType.FAA_PART_23, "FAA Part 23", "Amdt-1")
        assert lib.regulation_type == RegulationType.FAA_PART_23
        assert len(lib.sections) == 20
        assert lib.sections[0].section_number.startswith("23.")

    def test_import_faa_part_25(self, service):
        lib = service.importRegulation(RegulationType.FAA_PART_25, "FAA Part 25", "Amdt-1")
        assert len(lib.sections) == 20
        assert lib.sections[0].section_number.startswith("25.")

    def test_import_easa_cs_23(self, service):
        lib = service.importRegulation(RegulationType.EASA_CS_23, "EASA CS-23", "Amdt-1")
        assert lib.sections[0].section_number.startswith("CS-23.")

    def test_import_easa_cs_25(self, service):
        lib = service.importRegulation(RegulationType.EASA_CS_25, "EASA CS-25", "Amdt-1")
        assert lib.sections[0].section_number.startswith("CS-25.")

    def test_import_duplicate_returns_existing(self, service):
        lib1 = service.importRegulation(RegulationType.FAA_PART_23, "FAA Part 23", "Amdt-1")
        lib2 = service.importRegulation(RegulationType.FAA_PART_23, "FAA Part 23", "Amdt-1")
        assert lib1.regulation_id == lib2.regulation_id


class TestUpdateRegulation:

    def test_update_regulation_version(self, service):
        lib = service.importRegulation(RegulationType.FAA_PART_23, "FAA Part 23", "Amdt-1")
        result = service.updateRegulationVersion(lib.regulation_id, "Amdt-2")
        assert isinstance(result, RegulationUpdateResult)
        assert result.new_version == "Amdt-2"
        assert len(result.affected_compliance_items) > 0
        assert result.impact_assessment["requires_recheck"] is True

    def test_update_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.updateRegulationVersion("FAKE-ID", "v2")

    def test_amendment_history_recorded(self, service):
        lib = service.importRegulation(RegulationType.FAA_PART_23, "FAA Part 23", "Amdt-1")
        service.updateRegulationVersion(lib.regulation_id, "Amdt-2")
        updated = service.getLibrary(lib.regulation_id)
        assert len(updated.amendment_history) == 1


class TestRequirementMapping:

    def test_map_equivalent_requirements(self, service):
        mapping = service.mapEquivalentRequirements("23.2010", "CS-23.2010")
        assert isinstance(mapping, RequirementMapping)
        assert mapping.equivalence_type == "Equivalent"

    def test_map_unknown_requires_manual_review(self, service):
        mapping = service.mapEquivalentRequirements("99.9999", "CS-99.9999")
        assert mapping.equivalence_type == "ManualReview"

    def test_map_faa_25_equivalent(self, service):
        mapping = service.mapEquivalentRequirements("25.1301", "CS-25.1301")
        assert mapping.equivalence_type == "Equivalent"


class TestGetLibrary:

    def test_get_existing_library(self, service):
        lib = service.importRegulation(RegulationType.FAA_PART_23, "FAA Part 23", "Amdt-1")
        result = service.getLibrary(lib.regulation_id)
        assert result is not None
        assert result.regulation_id == lib.regulation_id

    def test_get_nonexistent_returns_none(self, service):
        result = service.getLibrary("FAKE-ID")
        assert result is None