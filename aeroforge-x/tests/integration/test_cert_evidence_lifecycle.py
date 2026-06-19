"""AeroForge-X V6.1 Integration Tests - Certification Evidence Lifecycle
IT-F01: importRegulation → generateChecklist → linkEvidence → assemblePackage → validate → lock → export
REQ-VP-045
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

import pytest

from src.domain.services.certification.regulatory_library_service import RegulatoryLibraryService, RegulationType
from src.domain.services.certification.compliance_checklist_service import ComplianceChecklistService
from src.domain.services.certification.certification_evidence_assembly_service import (
    CertificationEvidenceAssemblyService,
    EvidenceItem,
    EvidenceType,
    EvidenceVerificationStatus,
)


@pytest.fixture
def reg_svc():
    return RegulatoryLibraryService()


@pytest.fixture
def checklist_svc():
    return ComplianceChecklistService()


@pytest.fixture
def evidence_svc():
    return CertificationEvidenceAssemblyService()


class TestCertEvidenceLifecycle:

    def test_full_evidence_lifecycle(self, reg_svc, checklist_svc, evidence_svc):
        lib = reg_svc.importRegulation(RegulationType.FAA_PART_25, "FAA Part 25", "Amdt-1")
        assert len(lib.sections) == 20

        checklist = checklist_svc.generateChecklist(lib, "PROJ-Valkyrie")
        assert len(checklist.items) == 20

        evidence_items = []
        for item in checklist.items[:5]:
            checklist_svc.linkChecklistToEvidence(
                checklist.checklist_id, item.item_id, f"EVD-{item.item_id}"
            )
            evidence_items.append(EvidenceItem(
                evidence_id=f"EVD-{item.item_id}",
                evidence_type=EvidenceType.TEST_REPORT,
                document_ref=f"DOC-{item.item_id}",
                verification_status=EvidenceVerificationStatus.VERIFIED,
                regulation_section=item.regulation_reference,
            ))

        pkg = evidence_svc.assembleEvidencePackage(checklist.checklist_id, "PROJ-Valkyrie", evidence_items)
        assert len(pkg.sections) > 0

        required = [item.regulation_reference for item in checklist.items[:5]]
        validation = evidence_svc.validatePackageCompleteness(pkg.package_id, required)
        assert validation.is_complete is True

        locked = evidence_svc.lockEvidencePackage(pkg.package_id)
        assert locked.is_locked is True

        pdf = evidence_svc.exportEvidencePackage(pkg.package_id, "PDF")
        assert pdf["export_status"] == "Generated"

        zip_result = evidence_svc.exportEvidencePackage(pkg.package_id, "ZIP")
        assert zip_result["export_status"] == "Generated"