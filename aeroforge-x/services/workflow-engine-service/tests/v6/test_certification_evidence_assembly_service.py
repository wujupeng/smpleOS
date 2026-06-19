"""AeroForge-X V6.0/V6.1 Unit Tests - CertificationEvidenceAssemblyService
REQ-CERT-020~026, REQ-VP-020
"""

import pytest

from src.domain.services.certification.certification_evidence_assembly_service import (
    CertificationEvidenceAssemblyService,
    EvidenceItem,
    EvidenceType,
    EvidenceVerificationStatus,
    CertificationEvidencePackage,
    PackageValidationResult,
)


@pytest.fixture
def service():
    return CertificationEvidenceAssemblyService()


@pytest.fixture
def verified_evidence():
    return EvidenceItem(
        evidence_id="EVD-001",
        evidence_type=EvidenceType.TEST_REPORT,
        document_ref="DOC-TR-001",
        verification_status=EvidenceVerificationStatus.VERIFIED,
        regulation_section="23.2010",
    )


@pytest.fixture
def draft_evidence():
    return EvidenceItem(
        evidence_id="EVD-002",
        evidence_type=EvidenceType.ANALYSIS_REPORT,
        document_ref="DOC-AR-001",
        verification_status=EvidenceVerificationStatus.DRAFT,
        regulation_section="23.2110",
    )


class TestAssembleEvidencePackage:

    def test_assemble_package(self, service, verified_evidence):
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [verified_evidence])
        assert pkg.package_id.startswith("CEP-")
        assert pkg.checklist_id == "CL-001"
        assert pkg.project_id == "PROJ-001"
        assert len(pkg.sections) == 1

    def test_assemble_with_multiple_sections(self, service, verified_evidence, draft_evidence):
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [verified_evidence, draft_evidence])
        assert len(pkg.sections) == 2

    def test_assemble_groups_by_regulation_section(self, service):
        e1 = EvidenceItem(evidence_id="E1", evidence_type=EvidenceType.TEST_REPORT,
                          document_ref="D1", verification_status=EvidenceVerificationStatus.VERIFIED,
                          regulation_section="23.2010")
        e2 = EvidenceItem(evidence_id="E2", evidence_type=EvidenceType.INSPECTION_RECORD,
                          document_ref="D2", verification_status=EvidenceVerificationStatus.VERIFIED,
                          regulation_section="23.2010")
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [e1, e2])
        assert len(pkg.sections) == 1
        assert len(pkg.sections[0].evidence_items) == 2


class TestValidatePackageCompleteness:

    def test_validate_complete_package(self, service, verified_evidence):
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [verified_evidence])
        result = service.validatePackageCompleteness(pkg.package_id, ["23.2010"])
        assert isinstance(result, PackageValidationResult)
        assert result.is_complete is True
        assert len(result.missing_items) == 0

    def test_validate_incomplete_package(self, service, verified_evidence):
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [verified_evidence])
        result = service.validatePackageCompleteness(pkg.package_id, ["23.2010", "23.9999"])
        assert result.is_complete is False
        assert len(result.missing_items) > 0

    def test_validate_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.validatePackageCompleteness("FAKE-ID", [])


class TestGapReport:

    def test_generate_gap_report(self, service, verified_evidence):
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [verified_evidence])
        gaps = service.generateGapReport(pkg.package_id, ["23.2010", "23.9999"])
        assert len(gaps) > 0


class TestVersioning:

    def test_track_package_versioning(self, service, verified_evidence):
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [verified_evidence])
        result = service.trackPackageVersioning(pkg.package_id, "AddEvidence", "EVD-003")
        assert result["new_version"] == 2


class TestLockPackage:

    def test_lock_evidence_package(self, service, draft_evidence):
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [draft_evidence])
        locked = service.lockEvidencePackage(pkg.package_id)
        assert locked.is_locked is True
        for section in locked.sections:
            for ev in section.evidence_items:
                assert ev.verification_status == EvidenceVerificationStatus.VERIFIED


class TestExportPackage:

    def test_export_pdf(self, service, verified_evidence):
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [verified_evidence])
        result = service.exportEvidencePackage(pkg.package_id, "PDF")
        assert result["format"] == "PDF"
        assert result["export_status"] == "Generated"

    def test_export_zip(self, service, verified_evidence):
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [verified_evidence])
        result = service.exportEvidencePackage(pkg.package_id, "ZIP")
        assert result["format"] == "ZIP"
        assert result["export_status"] == "Generated"

    def test_export_unsupported_format_raises(self, service, verified_evidence):
        pkg = service.assembleEvidencePackage("CL-001", "PROJ-001", [verified_evidence])
        with pytest.raises(ValueError, match="Unsupported"):
            service.exportEvidencePackage(pkg.package_id, "DOCX")