"""AeroForge-X v6.0 CertificationEvidenceAssemblyService

Manages certification evidence package lifecycle: assembly, completeness
validation, locking, versioning, and export.
REQ-CERT-020~026
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EvidenceType(str, Enum):
    TEST_REPORT = "TestReport"
    ANALYSIS_REPORT = "AnalysisReport"
    INSPECTION_RECORD = "InspectionRecord"
    COMPLIANCE_DECLARATION = "ComplianceDeclaration"


class EvidenceVerificationStatus(str, Enum):
    DRAFT = "Draft"
    UNDER_REVIEW = "UnderReview"
    VERIFIED = "Verified"
    REJECTED = "Rejected"


@dataclass
class EvidenceItem:
    evidence_id: str
    evidence_type: EvidenceType
    document_ref: str
    verification_status: EvidenceVerificationStatus = EvidenceVerificationStatus.DRAFT
    regulation_section: str = ""

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "document_ref": self.document_ref,
            "verification_status": self.verification_status.value,
            "regulation_section": self.regulation_section,
        }


@dataclass
class EvidenceSection:
    regulation_section: str
    evidence_items: list[EvidenceItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "regulation_section": self.regulation_section,
            "evidence_items": [e.to_dict() for e in self.evidence_items],
        }


@dataclass
class CertificationEvidencePackage:
    package_id: str
    checklist_id: str
    project_id: str
    sections: list[EvidenceSection] = field(default_factory=list)
    is_complete: bool = False
    is_locked: bool = False
    version: int = 1
    submitted_at: str = ""

    def to_dict(self) -> dict:
        return {
            "package_id": self.package_id,
            "checklist_id": self.checklist_id,
            "project_id": self.project_id,
            "sections": [s.to_dict() for s in self.sections],
            "is_complete": self.is_complete,
            "is_locked": self.is_locked,
            "version": self.version,
            "submitted_at": self.submitted_at,
        }


@dataclass
class PackageValidationResult:
    package_id: str
    is_complete: bool
    missing_items: list[dict] = field(default_factory=list)
    gap_report: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "package_id": self.package_id,
            "is_complete": self.is_complete,
            "missing_items": self.missing_items,
            "gap_report": self.gap_report,
        }


class CertificationEvidenceAssemblyService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._packages: dict[str, CertificationEvidencePackage] = {}
        self._evidence_items: dict[str, EvidenceItem] = {}

    def assembleEvidencePackage(
        self, checklist_id: str, project_id: str, evidence_items: list[EvidenceItem]
    ) -> CertificationEvidencePackage:
        package_id = f"CEP-{project_id}-{uuid.uuid4().hex[:6]}"

        sections_map: dict[str, EvidenceSection] = {}
        for item in evidence_items:
            section_key = item.regulation_section or "General"
            if section_key not in sections_map:
                sections_map[section_key] = EvidenceSection(
                    regulation_section=section_key
                )
            sections_map[section_key].evidence_items.append(item)
            self._evidence_items[item.evidence_id] = item

        package = CertificationEvidencePackage(
            package_id=package_id,
            checklist_id=checklist_id,
            project_id=project_id,
            sections=list(sections_map.values()),
        )

        self._packages[package_id] = package
        return package

    def validatePackageCompleteness(
        self, package_id: str, required_checklist_items: list[str]
    ) -> PackageValidationResult:
        if package_id not in self._packages:
            raise ValueError(f"Evidence package not found: {package_id}")

        package = self._packages[package_id]
        covered_sections = {s.regulation_section for s in package.sections}

        missing_items = []
        gap_report = []

        for item_ref in required_checklist_items:
            found = False
            for section in package.sections:
                for evidence in section.evidence_items:
                    if evidence.regulation_section == item_ref:
                        if evidence.verification_status == EvidenceVerificationStatus.VERIFIED:
                            found = True
                            break
                if found:
                    break

            if not found:
                missing_items.append({"checklist_item": item_ref, "reason": "No verified evidence"})
                gap_report.append({
                    "checklist_item": item_ref,
                    "action_needed": "Add verified evidence item",
                })

        is_complete = len(missing_items) == 0
        package.is_complete = is_complete

        return PackageValidationResult(
            package_id=package_id,
            is_complete=is_complete,
            missing_items=missing_items,
            gap_report=gap_report,
        )

    def generateGapReport(
        self, package_id: str, required_checklist_items: list[str]
    ) -> list[dict]:
        result = self.validatePackageCompleteness(package_id, required_checklist_items)
        return result.gap_report

    def trackPackageVersioning(
        self, package_id: str, action: str, evidence_id: Optional[str] = None
    ) -> dict:
        if package_id not in self._packages:
            raise ValueError(f"Evidence package not found: {package_id}")

        package = self._packages[package_id]
        package.version += 1

        return {
            "package_id": package_id,
            "new_version": package.version,
            "action": action,
            "evidence_id": evidence_id,
        }

    def lockEvidencePackage(self, package_id: str) -> CertificationEvidencePackage:
        if package_id not in self._packages:
            raise ValueError(f"Evidence package not found: {package_id}")

        package = self._packages[package_id]
        package.is_locked = True

        for section in package.sections:
            for evidence in section.evidence_items:
                evidence.verification_status = EvidenceVerificationStatus.VERIFIED

        return package

    def exportEvidencePackage(
        self, package_id: str, format: str = "PDF"
    ) -> dict:
        if package_id not in self._packages:
            raise ValueError(f"Evidence package not found: {package_id}")

        package = self._packages[package_id]

        if format == "PDF":
            return {
                "package_id": package_id,
                "format": "PDF",
                "content": package.to_dict(),
                "export_status": "Generated",
            }
        elif format == "ZIP":
            return {
                "package_id": package_id,
                "format": "ZIP",
                "structure": {
                    section.regulation_section: [
                        e.document_ref for e in section.evidence_items
                    ]
                    for section in package.sections
                },
                "export_status": "Generated",
            }
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def getPackage(self, package_id: str) -> Optional[CertificationEvidencePackage]:
        return self._packages.get(package_id)