"""AeroForge-X v6.0 ComplianceChecklistService

Generates compliance checklists from FAA/EASA regulations and
links evidence items to checklist items.
REQ-CERT-014~019
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .regulatory_library_service import RegulatoryLibrary, RegulationType


class ComplianceMethod(str, Enum):
    TEST = "Test"
    ANALYSIS = "Analysis"
    INSPECTION = "Inspection"
    SIMILARITY = "Similarity"


class VerificationStatus(str, Enum):
    NOT_STARTED = "NotStarted"
    IN_PROGRESS = "InProgress"
    COMPLIANT = "Compliant"
    NON_COMPLIANT = "NonCompliant"


@dataclass
class ChecklistItem:
    item_id: str
    regulation_reference: str
    requirement_text: str
    compliance_method: ComplianceMethod = ComplianceMethod.INSPECTION
    responsible_party: str = ""
    verification_status: VerificationStatus = VerificationStatus.NOT_STARTED
    linked_evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "regulation_reference": self.regulation_reference,
            "requirement_text": self.requirement_text,
            "compliance_method": self.compliance_method.value,
            "responsible_party": self.responsible_party,
            "verification_status": self.verification_status.value,
            "linked_evidence_ids": self.linked_evidence_ids,
        }


@dataclass
class ComplianceChecklist:
    checklist_id: str
    regulation_id: str
    project_id: str
    items: list[ChecklistItem] = field(default_factory=list)
    completion_percentage: float = 0.0

    def to_dict(self) -> dict:
        return {
            "checklist_id": self.checklist_id,
            "regulation_id": self.regulation_id,
            "project_id": self.project_id,
            "items": [i.to_dict() for i in self.items],
            "completion_percentage": self.completion_percentage,
        }


class ComplianceChecklistService:

    def __init__(self) -> None:
        self._checklists: dict[str, ComplianceChecklist] = {}

    def generateChecklist(
        self, regulation: RegulatoryLibrary, project_id: str
    ) -> ComplianceChecklist:
        checklist_id = f"CL-{regulation.regulation_id}-{project_id}"

        items = []
        for section in regulation.sections:
            method = ComplianceMethod.INSPECTION
            if "test" in section.requirement_text.lower():
                method = ComplianceMethod.TEST
            elif "analysis" in section.requirement_text.lower() or "calculate" in section.requirement_text.lower():
                method = ComplianceMethod.ANALYSIS

            items.append(
                ChecklistItem(
                    item_id=f"CI-{uuid.uuid4().hex[:8]}",
                    regulation_reference=section.section_number,
                    requirement_text=section.requirement_text,
                    compliance_method=method,
                )
            )

        checklist = ComplianceChecklist(
            checklist_id=checklist_id,
            regulation_id=regulation.regulation_id,
            project_id=project_id,
            items=items,
        )
        self._checklists[checklist_id] = checklist
        return checklist

    def linkChecklistToEvidence(
        self, checklist_id: str, item_id: str, evidence_id: str
    ) -> Optional[ChecklistItem]:
        if checklist_id not in self._checklists:
            raise ValueError(f"Checklist not found: {checklist_id}")

        checklist = self._checklists[checklist_id]
        for item in checklist.items:
            if item.item_id == item_id:
                if evidence_id not in item.linked_evidence_ids:
                    item.linked_evidence_ids.append(evidence_id)
                return item

        raise ValueError(f"Checklist item not found: {item_id}")

    def getChecklist(self, checklist_id: str) -> Optional[ComplianceChecklist]:
        return self._checklists.get(checklist_id)