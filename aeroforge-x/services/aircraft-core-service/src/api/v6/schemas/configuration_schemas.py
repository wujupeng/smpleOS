"""AeroForge-X V6.0 Configuration Management Pydantic V2 Schemas
REQ-ENG-006, REQ-CFG-001~022
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class CreateBlockConfigRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    aircraft_type: str = Field(min_length=1, max_length=50)
    block_name: str = Field(min_length=1, max_length=100)


class CreateSNConfigRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    block_id: str = Field(min_length=1)
    tail_number: str = Field(min_length=1, max_length=50)


class BlockConfigResponse(BaseModel):
    block_id: str
    aircraft_type: str
    block_name: str
    design_config: dict | None = None
    manufacturing_config: dict | None = None
    operational_config: dict | None = None
    locked: bool = False


class SNConfigResponse(BaseModel):
    sn_id: str
    tail_number: str
    block_id: str
    design_config: dict | None = None


class ConfigHierarchyResponse(BaseModel):
    aircraft_type: str
    blocks: list[dict]


class InheritBlockConfigRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    new_block_name: str = Field(min_length=1)
    changes: dict = Field(default_factory=dict)


class InheritSNConfigRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    block_id: str = Field(min_length=1)
    modifications: dict = Field(default_factory=dict)


class ConflictReportResponse(BaseModel):
    conflicts: list[dict]


class ManufacturingRuleRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    rule_id: str = Field(min_length=1)
    rule_type: str = Field(pattern="^(ProcessAssignment|ToolingReference|InspectionRequirement)$")
    rule_expression: str = ""
    priority: int = Field(default=0, ge=0)


class OperationalRuleRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    rule_id: str = Field(min_length=1)
    rule_type: str = Field(pattern="^(EquipmentInstallation|SoftwareLoad|MaintenanceItem)$")
    rule_expression: str = ""
    priority: int = Field(default=0, ge=0)


class PropagationResultResponse(BaseModel):
    design_updated: bool
    manufacturing_updated: bool
    operational_updated: bool
    manual_resolution_needed: list[dict] = Field(default_factory=list)
    propagation_duration_ms: float = 0.0


class DesignChangeRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    block_id: str = Field(min_length=1)
    changed_items: list[dict]
    change_reason: str = ""


class ReconciliationReportResponse(BaseModel):
    config_id: str
    discrepancies: list[dict] = Field(default_factory=list)
    reconciliation_suggestions: list[str] = Field(default_factory=list)


class EstablishBaselineRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    block_id: str = Field(min_length=1)
    baseline_type: str = Field(pattern="^(FBL|FCL|FSDL)$")
    established_by: str = Field(min_length=1)


class BaselineResponse(BaseModel):
    baseline_id: str
    baseline_type: str
    block_id: str
    configuration_snapshot: dict
    frozen_items: list[str] = Field(default_factory=list)
    milestone: str
    established_by: str
    locked: bool = True
    change_history: list[dict] = Field(default_factory=list)


class BaselineDeltaReportResponse(BaseModel):
    baseline_id_1: str
    baseline_id_2: str
    added_items: list[str] = Field(default_factory=list)
    removed_items: list[str] = Field(default_factory=list)
    modified_items: list[dict] = Field(default_factory=list)


class ChangeRequestSubmitRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    block_id: str = Field(min_length=1)
    change_class: str = Field(pattern="^(ClassI|ClassII)$")
    change_type: str = ""
    description: str = ""
    requested_by: str = Field(min_length=1)
    affected_items: list[dict] = Field(default_factory=list)


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