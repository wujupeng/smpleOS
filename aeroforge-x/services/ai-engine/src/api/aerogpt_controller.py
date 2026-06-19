from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.ai_proposal import ProposalStatus
from ..domain.services.aerogpt_domain_service import AeroGPTDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["AI Engine"])

_service = AeroGPTDomainService()


class GenerateProposalRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    tenant_id: str = Field(default="default")
    natural_language_input: str = Field(..., min_length=1)
    created_by: str = ""


class IterateProposalRequest(BaseModel):
    feedback: str = Field(..., min_length=1)
    param_adjustments: dict[str, Any] | None = None


class RejectProposalRequest(BaseModel):
    reason: str = ""


@router.post("/aerogpt/generate", response_model=ApiResponse[dict])
async def generate_proposal(body: GenerateProposalRequest):
    proposal = _service.generate_initial_proposal(
        project_id=body.project_id,
        tenant_id=body.tenant_id,
        natural_language_input=body.natural_language_input,
        created_by=body.created_by,
    )
    return ApiResponse(data=proposal.to_dict())


@router.get("/proposals/{proposal_id}", response_model=ApiResponse[dict])
async def get_proposal(proposal_id: str):
    proposal = _service.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return ApiResponse(data=proposal.to_dict())


@router.get("/proposals", response_model=ApiResponse[dict])
async def list_proposals(project_id: str | None = None):
    proposals = _service.list_proposals(project_id)
    return ApiResponse(data={
        "total": len(proposals),
        "proposals": [p.to_dict() for p in proposals],
    })


@router.post("/proposals/{proposal_id}/confirm", response_model=ApiResponse[dict])
async def confirm_proposal(proposal_id: str):
    proposal = _service.confirm_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return ApiResponse(data=proposal.to_dict())


@router.post("/proposals/{proposal_id}/reject", response_model=ApiResponse[dict])
async def reject_proposal(proposal_id: str, body: RejectProposalRequest):
    proposal = _service.reject_proposal(proposal_id, body.reason)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return ApiResponse(data=proposal.to_dict())


@router.post("/proposals/{proposal_id}/iterate", response_model=ApiResponse[dict])
async def iterate_proposal(proposal_id: str, body: IterateProposalRequest):
    proposal = _service.iterate_with_feedback(
        proposal_id=proposal_id,
        feedback=body.feedback,
        param_adjustments=body.param_adjustments,
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return ApiResponse(data=proposal.to_dict())