"""AeroForge-X V6.0 Certification Pydantic V2 Schemas
REQ-ENG-007, REQ-CERT-001~026
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class ImportRegulationRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    regulation_type: str = Field(pattern="^(FAA_Part_23|FAA_Part_25|EASA_CS_23|EASA_CS_25)$")
    title: str = Field(min_length=1)
    version: str = Field(min_length=1)


class RegulationResponse(BaseModel):
    regulation_id: str
    regulation_type: str
    title: str
    version: str
    sections: list[dict] = Field(default_factory=list)


class RegulationUpdateRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    new_version: str = Field(min_length=1)


class RequirementMappingResponse(BaseModel):
    faa_section: str
    easa_section: str
    equivalence_type: str
    notes: str = ""


class GenerateChecklistRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    regulation_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)


class ChecklistItemResponse(BaseModel):
    item_id: str
    regulation_reference: str
    requirement_text: str
    compliance_method: str
    responsible_party: str = ""
    verification_status: str
    linked_evidence_ids: list[str] = Field(default_factory=list)


class ComplianceChecklistResponse(BaseModel):
    checklist_id: str
    regulation_id: str
    project_id: str
    items: list[ChecklistItemResponse] = Field(default_factory=list)
    completion_percentage: float = 0.0


class LinkEvidenceRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    checklist_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)


class TraceLinkCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    source_type: str = Field(pattern="^(Requirement|Design|Code|Test)$")
    source_id: str = Field(min_length=1)
    target_type: str = Field(pattern="^(Requirement|Design|Code|Test)$")
    target_id: str = Field(min_length=1)
    relationship: str = Field(pattern="^(satisfies|verifies|traces_to|derived_from)$")


class TraceLinkResponse(BaseModel):
    link_id: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str


class TraceMatrixResponse(BaseModel):
    links: list[TraceLinkResponse] = Field(default_factory=list)
    coverage_percentage: float = 0.0
    broken_links: list[dict] = Field(default_factory=list)


class EvidenceItemRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    evidence_type: str = Field(pattern="^(TestReport|AnalysisReport|InspectionRecord|ComplianceDeclaration)$")
    document_ref: str = Field(min_length=1)
    verification_status: str = Field(pattern="^(Draft|UnderReview|Verified|Rejected)$", default="Draft")
    regulation_section: str = ""


class AssembleEvidencePackageRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    checklist_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    evidence_items: list[EvidenceItemRequest]


class EvidencePackageResponse(BaseModel):
    package_id: str
    checklist_id: str
    project_id: str
    sections: list[dict] = Field(default_factory=list)
    is_complete: bool = False
    is_locked: bool = False
    version: int = 1


class ValidatePackageRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    package_id: str = Field(min_length=1)
    required_checklist_items: list[str]


class PackageValidationResponse(BaseModel):
    package_id: str
    is_complete: bool
    missing_items: list[dict] = Field(default_factory=list)
    gap_report: list[dict] = Field(default_factory=list)


class ExportPackageRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    package_id: str = Field(min_length=1)
    format: str = Field(pattern="^(PDF|ZIP)$")