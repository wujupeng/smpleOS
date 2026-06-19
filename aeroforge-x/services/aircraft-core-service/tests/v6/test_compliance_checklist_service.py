"""AeroForge-X V6.0/V6.1 Unit Tests - ComplianceChecklistService
REQ-CERT-014~019, REQ-VP-020
"""

import pytest

from src.domain.services.certification.compliance_checklist_service import (
    ComplianceChecklistService,
    ComplianceMethod,
    VerificationStatus,
    ComplianceChecklist,
    ChecklistItem,
)
from src.domain.services.certification.regulatory_library_service import (
    RegulatoryLibraryService,
    RegulationType,
)


@pytest.fixture
def reg_service():
    return RegulatoryLibraryService()


@pytest.fixture
def service():
    return ComplianceChecklistService()


@pytest.fixture
def faa_lib(reg_service):
    return reg_service.importRegulation(RegulationType.FAA_PART_23, "FAA Part 23", "Amdt-1")


class TestGenerateChecklist:

    def test_generate_checklist(self, service, faa_lib):
        checklist = service.generateChecklist(faa_lib, "PROJ-001")
        assert checklist.checklist_id.startswith("CL-")
        assert checklist.regulation_id == faa_lib.regulation_id
        assert checklist.project_id == "PROJ-001"
        assert len(checklist.items) == len(faa_lib.sections)

    def test_checklist_items_have_references(self, service, faa_lib):
        checklist = service.generateChecklist(faa_lib, "PROJ-001")
        for item in checklist.items:
            assert item.regulation_reference != ""
            assert item.verification_status == VerificationStatus.NOT_STARTED

    def test_checklist_default_method_is_inspection(self, service, faa_lib):
        checklist = service.generateChecklist(faa_lib, "PROJ-001")
        assert any(i.compliance_method == ComplianceMethod.INSPECTION for i in checklist.items)


class TestLinkEvidence:

    def test_link_evidence_to_item(self, service, faa_lib):
        checklist = service.generateChecklist(faa_lib, "PROJ-001")
        item = checklist.items[0]
        result = service.linkChecklistToEvidence(checklist.checklist_id, item.item_id, "EVD-001")
        assert "EVD-001" in result.linked_evidence_ids

    def test_link_duplicate_evidence_not_added(self, service, faa_lib):
        checklist = service.generateChecklist(faa_lib, "PROJ-001")
        item = checklist.items[0]
        service.linkChecklistToEvidence(checklist.checklist_id, item.item_id, "EVD-001")
        result = service.linkChecklistToEvidence(checklist.checklist_id, item.item_id, "EVD-001")
        assert result.linked_evidence_ids.count("EVD-001") == 1

    def test_link_nonexistent_checklist_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.linkChecklistToEvidence("FAKE-CL", "item-1", "EVD-001")

    def test_link_nonexistent_item_raises(self, service, faa_lib):
        checklist = service.generateChecklist(faa_lib, "PROJ-001")
        with pytest.raises(ValueError, match="not found"):
            service.linkChecklistToEvidence(checklist.checklist_id, "FAKE-ITEM", "EVD-001")


class TestGetChecklist:

    def test_get_existing_checklist(self, service, faa_lib):
        checklist = service.generateChecklist(faa_lib, "PROJ-001")
        result = service.getChecklist(checklist.checklist_id)
        assert result is not None
        assert result.checklist_id == checklist.checklist_id

    def test_get_nonexistent_returns_none(self, service):
        result = service.getChecklist("FAKE-ID")
        assert result is None