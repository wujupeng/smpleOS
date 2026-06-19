"""AeroForge-X v6.0 RegulatoryLibraryService

Manages airworthiness regulatory libraries: FAA Part 23/25, EASA CS-23/25
import, versioning, and equivalent requirement mapping.
REQ-CERT-008~013, REQ-CERT-017
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RegulationType(str, Enum):
    FAA_PART_23 = "FAA_Part_23"
    FAA_PART_25 = "FAA_Part_25"
    EASA_CS_23 = "EASA_CS_23"
    EASA_CS_25 = "EASA_CS_25"


@dataclass
class RegulationSection:
    section_number: str
    title: str
    requirement_text: str
    subparts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "section_number": self.section_number,
            "title": self.title,
            "requirement_text": self.requirement_text,
            "subparts": self.subparts,
        }


@dataclass
class RegulatoryLibrary:
    regulation_id: str
    regulation_type: RegulationType
    title: str
    version: str
    sections: list[RegulationSection] = field(default_factory=list)
    amendment_history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "regulation_id": self.regulation_id,
            "regulation_type": self.regulation_type.value,
            "title": self.title,
            "version": self.version,
            "sections": [s.to_dict() for s in self.sections],
            "amendment_history": self.amendment_history,
        }


@dataclass
class RegulationUpdateResult:
    regulation_id: str
    new_version: str
    affected_compliance_items: list[str] = field(default_factory=list)
    impact_assessment: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "regulation_id": self.regulation_id,
            "new_version": self.new_version,
            "affected_compliance_items": self.affected_compliance_items,
            "impact_assessment": self.impact_assessment,
        }


@dataclass
class RequirementMapping:
    faa_section: str
    easa_section: str
    equivalence_type: str
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "faa_section": self.faa_section,
            "easa_section": self.easa_section,
            "equivalence_type": self.equivalence_type,
            "notes": self.notes,
        }


class RegulatoryLibraryService:

    FAA_EASA_MAPPINGS = {
        "23.2010": {"easa": "CS-23.2010", "type": "Equivalent"},
        "23.2110": {"easa": "CS-23.2110", "type": "Equivalent"},
        "23.2130": {"easa": "CS-23.2130", "type": "Equivalent"},
        "25.1301": {"easa": "CS-25.1301", "type": "Equivalent"},
        "25.1309": {"easa": "CS-25.1309", "type": "Equivalent"},
        "25.1321": {"easa": "CS-25.1321", "type": "Equivalent"},
    }

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._libraries: dict[str, RegulatoryLibrary] = {}

    def importRegulation(
        self, regulation_type: RegulationType, title: str, version: str
    ) -> RegulatoryLibrary:
        regulation_id = f"{regulation_type.value}-{version}"

        if regulation_id in self._libraries:
            return self._libraries[regulation_id]

        library = RegulatoryLibrary(
            regulation_id=regulation_id,
            regulation_type=regulation_type,
            title=title,
            version=version,
        )

        if regulation_type in (RegulationType.FAA_PART_23, RegulationType.FAA_PART_25):
            library.sections = self._generate_faa_sections(regulation_type)
        elif regulation_type in (RegulationType.EASA_CS_23, RegulationType.EASA_CS_25):
            library.sections = self._generate_easa_sections(regulation_type)

        self._libraries[regulation_id] = library
        return library

    def _generate_faa_sections(
        self, regulation_type: RegulationType
    ) -> list[RegulationSection]:
        prefix = "23" if regulation_type == RegulationType.FAA_PART_23 else "25"
        sections = []
        for i in range(1, 21):
            section_num = f"{prefix}.{2000 + i * 10}"
            sections.append(
                RegulationSection(
                    section_number=section_num,
                    title=f"Section {section_num}",
                    requirement_text=f"Requirements for {section_num}",
                )
            )
        return sections

    def _generate_easa_sections(
        self, regulation_type: RegulationType
    ) -> list[RegulationSection]:
        prefix = "CS-23" if regulation_type == RegulationType.EASA_CS_23 else "CS-25"
        sections = []
        for i in range(1, 21):
            section_num = f"{prefix}.{2000 + i * 10}"
            sections.append(
                RegulationSection(
                    section_number=section_num,
                    title=f"Section {section_num}",
                    requirement_text=f"Certification specifications for {section_num}",
                )
            )
        return sections

    def updateRegulationVersion(
        self, regulation_id: str, new_version: str
    ) -> RegulationUpdateResult:
        if regulation_id not in self._libraries:
            raise ValueError(f"Regulatory library not found: {regulation_id}")

        library = self._libraries[regulation_id]
        old_version = library.version
        library.version = new_version
        library.amendment_history.append(
            {"from_version": old_version, "to_version": new_version}
        )

        affected_items = [s.section_number for s in library.sections]

        return RegulationUpdateResult(
            regulation_id=regulation_id,
            new_version=new_version,
            affected_compliance_items=affected_items,
            impact_assessment={
                "total_affected_sections": len(affected_items),
                "requires_recheck": True,
            },
        )

    def mapEquivalentRequirements(
        self, faa_section: str, easa_section: str
    ) -> RequirementMapping:
        mapping_data = self.FAA_EASA_MAPPINGS.get(faa_section)
        if mapping_data and mapping_data["easa"] == easa_section:
            return RequirementMapping(
                faa_section=faa_section,
                easa_section=easa_section,
                equivalence_type=mapping_data["type"],
            )

        return RequirementMapping(
            faa_section=faa_section,
            easa_section=easa_section,
            equivalence_type="ManualReview",
            notes="Automatic mapping not found, requires manual review",
        )

    def getLibrary(self, regulation_id: str) -> Optional[RegulatoryLibrary]:
        return self._libraries.get(regulation_id)