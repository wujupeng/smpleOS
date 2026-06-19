from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ..domain.entities.certification_plan import (
    CertificationAuthority,
    CertificationStandard,
    ComplianceMethod,
    ItemStatus,
)
from ..domain.services.certification_plan_service import CertificationPlanService
from ..domain.services.compliance_verification_service import ComplianceVerificationService
from ..domain.services.airworthiness_service import AirworthinessService
from ..domain.services.continuous_airworthiness_service import ContinuousAirworthinessService
from ..domain.entities.airworthiness_approval import ApprovalType, FindingStatus, FindingType
from ..domain.entities.continuous_airworthiness import ADComplianceStatus, SBExecutionStatus

router = APIRouter(prefix="/api/v1/certification", tags=["certification"])
_service = CertificationPlanService()
_verification_service = ComplianceVerificationService()
_airworthiness_service = AirworthinessService()
_continuous_service = ContinuousAirworthinessService()


class CreatePlanRequest(BaseModel):
    tenant_id: str
    project_id: str
    aircraft_type: str
    certification_standard: str = "FAR-25"
    certification_authority: str = "FAA"


class UpdateItemRequest(BaseModel):
    compliance_method: str | None = None
    status: str | None = None
    responsible_person: str | None = None
    due_date: str | None = None


class LinkEvidenceRequest(BaseModel):
    evidence_id: str
    evidence_type: str
    title: str
    reference: str = ""


@router.post("/plans")
async def create_plan(req: CreatePlanRequest):
    try:
        standard = CertificationStandard(req.certification_standard)
    except ValueError:
        standard = CertificationStandard.FAR_25
    try:
        authority = CertificationAuthority(req.certification_authority)
    except ValueError:
        authority = CertificationAuthority.FAA

    plan = _service.create_certification_plan(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        aircraft_type=req.aircraft_type,
        certification_standard=standard,
        certification_authority=authority,
    )
    return {"data": plan.to_detail_dict()}


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    plan = _service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"data": plan.to_detail_dict()}


@router.put("/plans/{plan_id}/items/{item_id}")
async def update_item(plan_id: str, item_id: str, req: UpdateItemRequest):
    method = None
    if req.compliance_method:
        try:
            method = ComplianceMethod(req.compliance_method)
        except ValueError:
            pass
    status = None
    if req.status:
        try:
            status = ItemStatus(req.status)
        except ValueError:
            pass

    plan = _service.update_item_status(plan_id, item_id, status) if status else None
    if method:
        plan = _service.assign_compliance_method(plan_id, item_id, method)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan or item not found")
    return {"data": plan.to_detail_dict()}


# --- Airworthiness Approval APIs ---

class SubmitApprovalRequest(BaseModel):
    tenant_id: str
    certification_plan_id: str
    approval_type: str = "Type_Certificate"


class AddFindingRequest(BaseModel):
    finding_type: str = "finding"
    description: str
    clause_reference: str = ""
    corrective_action: str = ""
    assigned_to: str = ""


class UpdateFindingRequest(BaseModel):
    corrective_action: str | None = None
    status: str | None = None
    assigned_to: str | None = None


class VerifyFindingRequest(BaseModel):
    verified_by: str = ""


@router.post("/approvals")
async def submit_approval(req: SubmitApprovalRequest):
    try:
        atype = ApprovalType(req.approval_type)
    except ValueError:
        atype = ApprovalType.TYPE_CERTIFICATE
    approval = _airworthiness_service.submit_approval_application(
        tenant_id=req.tenant_id,
        certification_plan_id=req.certification_plan_id,
        approval_type=atype,
    )
    return {"data": approval.to_detail_dict()}


@router.get("/approvals/{approval_id}")
async def get_approval(approval_id: str):
    approval = _airworthiness_service.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {"data": approval.to_detail_dict()}


@router.post("/approvals/{approval_id}/findings")
async def add_finding(approval_id: str, req: AddFindingRequest):
    try:
        ftype = FindingType(req.finding_type)
    except ValueError:
        ftype = FindingType.FINDING
    approval = _airworthiness_service.manage_review_findings(
        approval_id=approval_id,
        finding_type=ftype,
        description=req.description,
        clause_reference=req.clause_reference,
        corrective_action=req.corrective_action,
        assigned_to=req.assigned_to,
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {"data": approval.to_detail_dict()}


@router.put("/approvals/{approval_id}/findings/{finding_id}")
async def update_finding(approval_id: str, finding_id: str, req: UpdateFindingRequest):
    status = None
    if req.status:
        try:
            status = FindingStatus(req.status)
        except ValueError:
            pass
    approval = _airworthiness_service.update_finding(
        approval_id=approval_id,
        finding_id=finding_id,
        corrective_action=req.corrective_action,
        status=status,
        assigned_to=req.assigned_to,
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Approval or finding not found")
    return {"data": approval.to_detail_dict()}


@router.post("/approvals/{approval_id}/issue-certificate")
async def issue_certificate(approval_id: str):
    approval = _airworthiness_service.issue_certificate(approval_id)
    if not approval:
        raise HTTPException(status_code=400, detail="Cannot issue certificate: findings not closed or conditions not met")
    return {"data": approval.to_detail_dict()}


# --- Continuous Airworthiness APIs ---

class CreateContinuousRecordRequest(BaseModel):
    tenant_id: str
    aircraft_serial_number: str
    certificate_id: str = ""


class ImportADRequest(BaseModel):
    ad_number: str
    ad_title: str
    issue_date: str
    compliance_deadline: str
    applicability: str = ""


class ImportSBRequest(BaseModel):
    sb_number: str
    sb_title: str
    issue_date: str
    execution_deadline: str
    priority: str = "medium"


class AddInspectionRequest(BaseModel):
    inspection_name: str
    interval_type: str = "flight_hours"
    interval_value: float = 500.0
    last_performed_at: float = 0.0


@router.post("/continuous-airworthiness")
async def create_continuous_record(req: CreateContinuousRecordRequest):
    record = _continuous_service.create_record(
        tenant_id=req.tenant_id,
        aircraft_serial_number=req.aircraft_serial_number,
        certificate_id=req.certificate_id,
    )
    return {"data": record.to_detail_dict()}


@router.get("/continuous-airworthiness/{aircraft_sn}")
async def get_continuous_record(aircraft_sn: str):
    record = _continuous_service.get_by_aircraft(aircraft_sn)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"data": record.to_detail_dict()}


@router.post("/continuous-airworthiness/{aircraft_sn}/ad")
async def import_ad(aircraft_sn: str, req: ImportADRequest):
    record = _continuous_service.import_airworthiness_directive(
        aircraft_sn=aircraft_sn,
        ad_number=req.ad_number,
        ad_title=req.ad_title,
        issue_date=req.issue_date,
        compliance_deadline=req.compliance_deadline,
        applicability=req.applicability,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Aircraft record not found")
    return {"data": record.to_detail_dict()}


@router.post("/continuous-airworthiness/{aircraft_sn}/sb")
async def import_sb(aircraft_sn: str, req: ImportSBRequest):
    record = _continuous_service.import_service_bulletin(
        aircraft_sn=aircraft_sn,
        sb_number=req.sb_number,
        sb_title=req.sb_title,
        issue_date=req.issue_date,
        execution_deadline=req.execution_deadline,
        priority=req.priority,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Aircraft record not found")
    return {"data": record.to_detail_dict()}


@router.post("/continuous-airworthiness/{aircraft_sn}/inspections")
async def add_inspection(aircraft_sn: str, req: AddInspectionRequest):
    record = _continuous_service.add_recurring_inspection(
        aircraft_sn=aircraft_sn,
        inspection_name=req.inspection_name,
        interval_type=req.interval_type,
        interval_value=req.interval_value,
        last_performed_at=req.last_performed_at,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Aircraft record not found")
    return {"data": record.to_detail_dict()}


@router.get("/continuous-airworthiness/{aircraft_sn}/assessment")
async def assess_airworthiness(aircraft_sn: str):
    result = _continuous_service.assess_overall_airworthiness(aircraft_sn)
    if not result:
        raise HTTPException(status_code=404, detail="Aircraft record not found")
    return {"data": result}


class VerifyDesignRequest(BaseModel):
    plan_id: str
    design_data: dict[str, Any] | None = None


class VerifyManufacturingRequest(BaseModel):
    plan_id: str
    mfg_data: dict[str, Any] | None = None


class VerifyTestRequest(BaseModel):
    plan_id: str
    test_data: dict[str, Any] | None = None


@router.post("/verify/design")
async def verify_design(req: VerifyDesignRequest):
    report = _verification_service.verify_design_compliance(
        plan_id=req.plan_id,
        design_data=req.design_data,
    )
    return {"data": report.to_dict()}


@router.post("/verify/manufacturing")
async def verify_manufacturing(req: VerifyManufacturingRequest):
    report = _verification_service.verify_manufacturing_compliance(
        plan_id=req.plan_id,
        mfg_data=req.mfg_data,
    )
    return {"data": report.to_dict()}


@router.post("/verify/test")
async def verify_test(req: VerifyTestRequest):
    report = _verification_service.verify_test_compliance(
        plan_id=req.plan_id,
        test_data=req.test_data,
    )
    return {"data": report.to_dict()}


@router.get("/plans/{plan_id}/verification-report")
async def get_verification_report(plan_id: str):
    reports = _verification_service.generate_verification_report(plan_id)
    return {"data": [r.to_dict() for r in reports]}


@router.get("/plans/{plan_id}/progress")
async def get_progress(plan_id: str):
    progress = _service.track_compliance_progress(plan_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"data": progress}


@router.post("/plans/{plan_id}/generate-document")
async def generate_document(plan_id: str):
    doc = _service.generate_certification_plan_document(plan_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"data": doc}


@router.post("/plans/{plan_id}/submit")
async def submit_plan(plan_id: str):
    plan = _service.submit_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"data": plan.to_dict()}


@router.post("/plans/{plan_id}/items/{item_id}/evidence")
async def link_evidence(plan_id: str, item_id: str, req: LinkEvidenceRequest):
    plan = _service.link_evidence(
        plan_id=plan_id,
        item_id=item_id,
        evidence_id=req.evidence_id,
        evidence_type=req.evidence_type,
        title=req.title,
        reference=req.reference,
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan or item not found")
    return {"data": plan.to_detail_dict()}