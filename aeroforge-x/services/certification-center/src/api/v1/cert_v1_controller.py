from fastapi import APIRouter, HTTPException

from src.domain.entities.v1.compliance_item import ComplianceMethod
from src.domain.services.v1.certification_plan_service import CertificationPlanService
from src.domain.services.v1.compliance_verification_service import ComplianceVerificationService
from src.domain.services.v1.airworthiness_service import AirworthinessService, AirworthinessDirective, ServiceBulletin
from src.infrastructure.event_bus import event_bus

router = APIRouter()

_plan_service = CertificationPlanService(event_publisher=event_bus)
_verification_service = ComplianceVerificationService(event_publisher=event_bus)
_aw_service = AirworthinessService(event_publisher=event_bus)


@router.post("/certification/plans")
async def create_certification_plan(body: dict):
    project_id = body.get("project_id", "")
    aircraft_type = body.get("aircraft_type", "")
    standard = body.get("standard", "FAR-25")
    authority = body.get("authority", "FAA")
    created_by = body.get("created_by", "")
    if not project_id or not aircraft_type:
        raise HTTPException(status_code=400, detail="project_id and aircraft_type are required")
    plan = await _plan_service.create_certification_plan(project_id, aircraft_type, standard, authority, created_by)
    return plan.to_dict()


@router.get("/certification/plans/{plan_id}")
async def get_certification_plan(plan_id: str):
    plan = _plan_service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return plan.to_dict()


@router.put("/certification/plans/{plan_id}/items/{item_id}")
async def update_compliance_item(plan_id: str, item_id: str, body: dict):
    item = _plan_service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    if "compliance_method" in body:
        method = ComplianceMethod(body["compliance_method"])
        _plan_service.assign_compliance_method(item_id, method)
    if "responsible_person" in body:
        item.responsible_person = body["responsible_person"]
    if "due_date" in body:
        item.due_date = body["due_date"]
    return item.to_dict()


@router.get("/certification/plans/{plan_id}/progress")
async def get_compliance_progress(plan_id: str):
    return _plan_service.track_compliance_progress(plan_id)


@router.post("/certification/plans/{plan_id}/generate-document")
async def generate_certification_document(plan_id: str):
    return _plan_service.generate_certification_plan_document(plan_id)


@router.post("/certification/verify/design")
async def verify_design_compliance(body: dict):
    item_id = body.get("item_id", "")
    design_data = body.get("design_data", {})
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")
    item = _plan_service.get_item(item_id)
    result = _verification_service.verify_design_compliance(item_id, design_data, item)
    return result.to_dict()


@router.post("/certification/verify/manufacturing")
async def verify_manufacturing_compliance(body: dict):
    item_id = body.get("item_id", "")
    mfg_data = body.get("manufacturing_data", {})
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")
    result = _verification_service.verify_manufacturing_compliance(item_id, mfg_data)
    return result.to_dict()


@router.post("/certification/verify/test")
async def verify_test_compliance(body: dict):
    item_id = body.get("item_id", "")
    test_data = body.get("test_data", {})
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")
    result = _verification_service.verify_test_compliance(item_id, test_data)
    return result.to_dict()


@router.get("/certification/plans/{plan_id}/verification-report")
async def get_verification_report(plan_id: str):
    return _verification_service.generate_verification_report(plan_id)


@router.post("/certification/approvals")
async def submit_approval_application(body: dict):
    plan_id = body.get("certification_plan_id", "")
    approval_type = body.get("approval_type", "type_certificate")
    submitted_by = body.get("submitted_by", "")
    if not plan_id:
        raise HTTPException(status_code=400, detail="certification_plan_id is required")
    approval = await _aw_service.submit_approval_application(plan_id, approval_type, submitted_by)
    return approval.to_dict()


@router.get("/certification/approvals/{approval_id}")
async def get_approval_status(approval_id: str):
    try:
        return _aw_service.track_review_progress(approval_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/certification/continuous-airworthiness/ad")
async def track_ad_compliance(aircraft_sn: str = ""):
    if not aircraft_sn:
        return {"total_applicable_ads": 0, "compliant_ads": 0, "pending_ads": 0}
    return _aw_service.track_ad_compliance(aircraft_sn)