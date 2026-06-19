"""AeroForge-X V6.0/V6.1 Workflow Engine Pydantic V2 Schemas
REQ-ENG-010, REQ-CFG-018~022, REQ-CERT-020~026, REQ-SUP-019~024, REQ-FACTORY-019~022
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class ChangeRequestSubmitBody(BaseModel):
    model_config = ConfigDict(strict=True)
    block_id: str = Field(min_length=1)
    change_class: str = Field(pattern="^(ClassI|ClassII)$")
    change_type: str = ""
    description: str = ""
    requested_by: str = Field(min_length=1)
    affected_items: list[dict] = Field(default_factory=list)


class ChangeApprovalRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    approver: str = Field(min_length=1)
    change_class: str = Field(pattern="^(ClassI|ClassII)$")


class ChangeRequestResponse(BaseModel):
    request_id: str
    block_id: str
    change_class: str
    change_type: str
    description: str
    status: str
    impact_analysis: dict | None = None
    approval: dict | None = None


class ImpactAnalysisResponse(BaseModel):
    request_id: str
    affected_design_items: list[str] = Field(default_factory=list)
    affected_mfg_items: list[str] = Field(default_factory=list)
    affected_op_items: list[str] = Field(default_factory=list)
    affected_sns: list[str] = Field(default_factory=list)
    estimated_propagation_time_ms: float = 0.0


class ChangeImplementationResponse(BaseModel):
    request_id: str
    items_updated: int
    propagation_completed: bool
    propagation_duration_ms: float = 0.0
    errors: list[str] = Field(default_factory=list)


class ChangeVerificationResponse(BaseModel):
    request_id: str
    is_verified: bool
    verification_details: list[dict] = Field(default_factory=list)
    baseline_updated: bool = False


class AuditTrailResponse(BaseModel):
    entries: list[dict]


class CertEvidenceAssembleRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    checklist_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    evidence_items: list[dict]


class CertEvidencePackageResponse(BaseModel):
    package_id: str
    checklist_id: str
    project_id: str
    sections: list[dict] = Field(default_factory=list)
    is_complete: bool = False
    is_locked: bool = False
    version: int = 1


class CertEvidenceValidateRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    package_id: str = Field(min_length=1)
    required_checklist_items: list[str]


class CertEvidenceExportRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    package_id: str = Field(min_length=1)
    format: str = Field(pattern="^(PDF|ZIP)$")


class QualityIssueCreateBody(BaseModel):
    model_config = ConfigDict(strict=True)
    supplier_id: str = Field(min_length=1)
    part_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    lot_id: str = ""


class CARCreateBody(BaseModel):
    model_config = ConfigDict(strict=True)
    issue_id: str = Field(min_length=1)
    severity: str = Field(pattern="^(Minor|Major|Critical)$")
    assigned_to: str = Field(min_length=1)


class CARVerifyBody(BaseModel):
    model_config = ConfigDict(strict=True)
    corrective_action: str = Field(min_length=1)
    verified_by: str = Field(min_length=1)
    is_effective: bool


class SupplierCARResponse(BaseModel):
    car_id: str
    issue_id: str
    severity: str
    status: str
    assigned_to: str
    due_date: str = ""
    corrective_action: str = ""
    verification_result: str = ""


class ShopFloorEventEmitRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    equipment_id: str = Field(min_length=1)
    event_type: str = Field(pattern="^(EquipmentStatusChange|OperationStart|OperationComplete|QualityAlert|AGVTaskUpdate|DeviationAlert)$")
    payload: dict = Field(default_factory=dict)


class ShopFloorEventResponse(BaseModel):
    event_id: str
    published: bool
    subject: str


class EventPlaybackRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    event_type: str | None = None
    source_equipment_id: str = ""
    time_from: float = 0
    time_to: float = 0
    time_window_s: float | None = None


class CrossProgramEventPublishRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    subject: str = Field(min_length=1)
    payload: dict = Field(default_factory=dict)
    source: str = ""


class CrossProgramEventResponse(BaseModel):
    event_id: str
    source_subject: str
    integration_point: str
    status: str