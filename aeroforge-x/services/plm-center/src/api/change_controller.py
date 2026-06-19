from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.services.baseline_domain_service import BaselineDomainService
from ..domain.services.change_mgmt_domain_service import ChangeMgmtDomainService
from ..domain.services.impact_analysis_service import ImpactAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/plm", tags=["PLM Change Management"])

_baseline_service = BaselineDomainService()
_change_service = ChangeMgmtDomainService()
_impact_service = ImpactAnalysisService()


class EstablishBaselineRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    created_by: str = ""
    objects: list[dict[str, Any]] | None = None


class SubmitECRRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    submitter: str = ""
    change_items: list[dict[str, Any]] | None = None


class ApproveECRRequest(BaseModel):
    approved_by: str = ""


class RejectECRRequest(BaseModel):
    reason: str = ""


class CreateECORequest(BaseModel):
    ecr_id: str
    assignee: str = ""


class ExecuteChangeRequest(BaseModel):
    object_id: str


class GenerateECNRequest(BaseModel):
    eco_id: str
    title: str = ""
    description: str = ""


@router.post("/baselines", response_model=ApiResponse[dict])
async def establish_baseline(body: EstablishBaselineRequest):
    baseline = _baseline_service.establish_baseline(
        name=body.name,
        description=body.description,
        created_by=body.created_by,
        objects=body.objects,
    )
    return ApiResponse(data=baseline.to_dict())


@router.post("/baselines/{baseline_id}/freeze", response_model=ApiResponse[dict])
async def freeze_baseline(baseline_id: str):
    baseline = _baseline_service.freeze_baseline(baseline_id)
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return ApiResponse(data=baseline.to_dict())


@router.post("/baselines/{baseline_id}/unfreeze", response_model=ApiResponse[dict])
async def unfreeze_baseline(baseline_id: str, approved_by: str = ""):
    baseline = _baseline_service.unfreeze_baseline(baseline_id, approved_by)
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return ApiResponse(data=baseline.to_dict())


@router.get("/baselines/{baseline_id}", response_model=ApiResponse[dict])
async def get_baseline(baseline_id: str):
    baseline = _baseline_service.get_baseline(baseline_id)
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return ApiResponse(data=baseline.to_dict())


@router.get("/baselines", response_model=ApiResponse[dict])
async def list_baselines():
    baselines = _baseline_service.list_baselines()
    return ApiResponse(data={
        "total": len(baselines),
        "baselines": [b.to_dict() for b in baselines],
    })


@router.get("/baselines/{baseline_id}/integrity", response_model=ApiResponse[dict])
async def check_baseline_integrity(baseline_id: str):
    result = _baseline_service.check_baseline_integrity(baseline_id)
    return ApiResponse(data=result)


@router.post("/ecr", response_model=ApiResponse[dict])
async def submit_ecr(body: SubmitECRRequest):
    ecr = _change_service.submit_ecr(
        title=body.title,
        description=body.description,
        submitter=body.submitter,
        change_items=body.change_items,
    )

    impact = _impact_service.full_analysis(ecr)

    return ApiResponse(data={
        **ecr.to_dict(),
        "impact_analysis": impact.to_dict(),
    })


@router.post("/ecr/{ecr_id}/approve", response_model=ApiResponse[dict])
async def approve_ecr(ecr_id: str, body: ApproveECRRequest):
    ecr = _change_service.approve_ecr(ecr_id, body.approved_by)
    if ecr is None:
        raise HTTPException(status_code=404, detail="ECR not found")
    return ApiResponse(data=ecr.to_dict())


@router.post("/ecr/{ecr_id}/reject", response_model=ApiResponse[dict])
async def reject_ecr(ecr_id: str, body: RejectECRRequest):
    ecr = _change_service.reject_ecr(ecr_id, body.reason)
    if ecr is None:
        raise HTTPException(status_code=404, detail="ECR not found")
    return ApiResponse(data=ecr.to_dict())


@router.post("/ecr/{ecr_id}/withdraw", response_model=ApiResponse[dict])
async def withdraw_ecr(ecr_id: str):
    ecr = _change_service.withdraw_ecr(ecr_id)
    if ecr is None:
        raise HTTPException(status_code=404, detail="ECR not found")
    return ApiResponse(data=ecr.to_dict())


@router.get("/ecr/{ecr_id}", response_model=ApiResponse[dict])
async def get_ecr(ecr_id: str):
    ecr = _change_service.get_ecr(ecr_id)
    if ecr is None:
        raise HTTPException(status_code=404, detail="ECR not found")
    return ApiResponse(data=ecr.to_dict())


@router.get("/ecr/{ecr_id}/impact", response_model=ApiResponse[dict])
async def get_ecr_impact(ecr_id: str):
    ecr = _change_service.get_ecr(ecr_id)
    if ecr is None:
        raise HTTPException(status_code=404, detail="ECR not found")
    impact = _impact_service.full_analysis(ecr)
    return ApiResponse(data=impact.to_dict())


@router.get("/ecr", response_model=ApiResponse[dict])
async def list_ecrs():
    ecrs = _change_service.list_ecrs()
    return ApiResponse(data={
        "total": len(ecrs),
        "ecrs": [e.to_dict() for e in ecrs],
    })


@router.post("/eco", response_model=ApiResponse[dict])
async def create_eco(body: CreateECORequest):
    eco = _change_service.create_eco(body.ecr_id, body.assignee)
    if eco is None:
        raise HTTPException(status_code=400, detail="ECR not found or not approved")
    return ApiResponse(data=eco.to_dict())


@router.post("/eco/{eco_id}/execute", response_model=ApiResponse[dict])
async def execute_change(eco_id: str, body: ExecuteChangeRequest):
    eco = _change_service.execute_change(eco_id, body.object_id)
    if eco is None:
        raise HTTPException(status_code=404, detail="ECO not found")
    return ApiResponse(data=eco.to_dict())


@router.get("/eco/{eco_id}", response_model=ApiResponse[dict])
async def get_eco(eco_id: str):
    eco = _change_service.get_eco(eco_id)
    if eco is None:
        raise HTTPException(status_code=404, detail="ECO not found")
    return ApiResponse(data=eco.to_dict())


@router.post("/ecn/generate", response_model=ApiResponse[dict])
async def generate_ecn(body: GenerateECNRequest):
    ecn = _change_service.generate_ecn(body.eco_id, body.title, body.description)
    if ecn is None:
        raise HTTPException(status_code=400, detail="ECO not found or not completed")
    return ApiResponse(data=ecn.to_dict())


@router.get("/ecn/{ecn_id}", response_model=ApiResponse[dict])
async def get_ecn(ecn_id: str):
    ecn = _change_service.get_ecn(ecn_id)
    if ecn is None:
        raise HTTPException(status_code=404, detail="ECN not found")
    return ApiResponse(data=ecn.to_dict())


@router.get("/approval-timeout", response_model=ApiResponse[dict])
async def check_approval_timeout():
    timed_out = _change_service.check_approval_timeout()
    return ApiResponse(data={
        "timed_out_count": len(timed_out),
        "timed_out_ecrs": timed_out,
    })