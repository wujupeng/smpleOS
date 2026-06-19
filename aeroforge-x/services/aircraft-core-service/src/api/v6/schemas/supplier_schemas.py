"""AeroForge-X V6.0 Supplier Pydantic V2 Schemas
REQ-ENG-008, REQ-SUP-001~018
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class RegisterSupplierRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    supplier_id: str = Field(min_length=1, max_length=50)
    company_name: str = Field(min_length=1, max_length=200)
    certifications: list[str] = Field(default_factory=list)
    capability_matrix: dict = Field(default_factory=dict)


class SupplierProfileResponse(BaseModel):
    supplier_id: str
    company_name: str
    certifications: list[str] = Field(default_factory=list)
    capability_matrix: dict = Field(default_factory=dict)
    quality_history: dict = Field(default_factory=dict)
    status: str
    approved_parts: list[str] = Field(default_factory=list)


class QualityRatingResponse(BaseModel):
    on_time_delivery_rate: float = 0.0
    first_pass_yield: float = 0.0
    defect_rate: float = 0.0
    car_responsiveness: float = 0.0
    audit_findings_score: float = 0.0
    overall_rating: float = 0.0
    is_below_threshold: bool = False


class UpdateRatingRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    on_time_delivery_rate: float | None = None
    first_pass_yield: float | None = None
    defect_rate: float | None = None
    car_responsiveness: float | None = None
    audit_findings_score: float | None = None


class SuspendSupplierRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    reason: str = Field(min_length=1)


class SuspensionResponse(BaseModel):
    supplier_id: str
    reason: str
    affected_parts: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class SupplyChainImpactResponse(BaseModel):
    supplier_id: str
    affected_parts_count: int
    affected_boms: list[str] = Field(default_factory=list)
    alternative_suppliers: dict = Field(default_factory=dict)


class ReceiveMaterialLotRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    lot_id: str = Field(min_length=1)
    supplier_id: str = Field(min_length=1)
    material_specification: str = Field(min_length=1)
    heat_number: str = Field(min_length=1)
    certificate_of_conformance: str = ""


class MaterialLotResponse(BaseModel):
    lot_id: str
    supplier_id: str
    material_specification: str
    heat_number: str
    certificate_of_conformance: str = ""
    test_results: dict = Field(default_factory=dict)
    status: str
    installed_parts: list[str] = Field(default_factory=list)
    installed_aircraft: list[str] = Field(default_factory=list)


class ForwardTraceResponse(BaseModel):
    lot_id: str
    affected_parts: list[str] = Field(default_factory=list)
    affected_aircraft: list[str] = Field(default_factory=list)


class BackwardTraceResponse(BaseModel):
    part_serial_id: str
    material_lot: dict | None = None
    supplier_id: str = ""
    certification_data: dict = Field(default_factory=dict)


class NDTRecordRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    ndt_id: str = Field(min_length=1)
    part_id: str = Field(min_length=1)
    inspection_method: str = Field(pattern="^(UT|RT|PT|MT|ET)$")
    equipment_calibration_data: dict = Field(default_factory=dict)
    inspection_procedure_ref: str = ""
    inspector_certification: str = ""
    acceptance_criteria: str = ""
    result: str = Field(pattern="^(Accept|Reject|Conditional)$")
    linked_lot_id: str = ""
    defects_found: list[dict] = Field(default_factory=list)


class NDTRecordResponse(BaseModel):
    ndt_id: str
    part_id: str
    inspection_method: str
    result: str
    linked_lot_id: str = ""
    defects_found: list[dict] = Field(default_factory=list)


class NDTStatisticsResponse(BaseModel):
    total_records: int = 0
    accept_count: int = 0
    reject_count: int = 0
    conditional_count: int = 0
    defect_rate_by_supplier: dict = Field(default_factory=dict)
    method_effectiveness: dict = Field(default_factory=dict)


class QualityIssueCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    supplier_id: str = Field(min_length=1)
    part_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    lot_id: str = ""


class CARCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    issue_id: str = Field(min_length=1)
    severity: str = Field(pattern="^(Minor|Major|Critical)$")
    assigned_to: str = Field(min_length=1)


class CARResponse(BaseModel):
    car_id: str
    issue_id: str
    severity: str
    status: str
    assigned_to: str
    due_date: str = ""
    corrective_action: str = ""
    verification_result: str = ""