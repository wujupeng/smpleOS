from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.generative_design.requirement_parser_service import (
    RequirementParserService,
    FeasibilityStatus,
)

router = APIRouter(prefix="/api/v5/physics-twin/design-requirements", tags=["Design Requirements v5"])

_service = RequirementParserService()


@router.post("")
async def parse_requirement(body: dict[str, Any]):
    text = body.get("requirement_text", "")
    if not text:
        raise HTTPException(status_code=400, detail="requirement_text is required")

    project_id = body.get("project_id", "")
    requirement = _service.parse_requirement(text=text, project_id=project_id)
    return requirement.to_dict()


@router.get("/{requirement_id}")
async def get_requirement(requirement_id: str):
    req = _service.get_requirement_version(requirement_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return req.to_dict()


@router.post("/{requirement_id}/validate")
async def validate_requirement(requirement_id: str):
    req = _service.get_requirement_version(requirement_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Requirement not found")

    result = _service.validate_physical_feasibility(req)
    return {
        "requirement_id": requirement_id,
        "is_feasible": result.is_feasible,
        "violated_constraints": result.violated_constraints,
        "suggested_adjustments": result.suggested_adjustments,
    }


@router.post("/{requirement_id}/conflict-report")
async def generate_conflict_report(requirement_id: str):
    req = _service.get_requirement_version(requirement_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Requirement not found")

    report = _service.generate_conflict_report(req)
    return {
        "requirement_id": report.requirement_id,
        "conflicts": report.conflicts,
        "resolution_suggestions": report.resolution_suggestions,
    }